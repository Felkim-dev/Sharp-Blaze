from typing import Dict, Any, List, Tuple
import math


class UnitCommander:
    """
    Generates concrete unit commands from strategic decisions.
    
    Responsibilities:
    - Build units (Attacker/Collector) based on decision
    - Move units to strategic locations
    - Queue attack orders when needed
    
    Commands are sent via network.py using JSON protocol
    """

    def __init__(self, game_world, network, player_id: int):
        """
        Initialize unit commander
        
        Args:
            game_world: GameWorld instance (for unit positions, terrain)
            network: Network instance (for sending commands)
            player_id: 1 or 2, which player is bot
        """
        self.game_world = game_world
        self.network = network
        self.player_id = player_id
        self.enemy_id = 2 if player_id == 1 else 1
        
        # Unit ID ranges
        if player_id == 1:
            self.attackers_range = range(1000, 3000)
            self.collectors_range = range(3000, 5000)
            self.player_base = (300, 4700)
        else:
            self.attackers_range = range(6000, 8000)
            self.collectors_range = range(8000, 10000)
            self.player_base = (4700, 300)
        
        # Known mining locations (approximate, from map layout)
        self.mining_locations = [
            (1000, 1000),  # Top-left mines
            (4000, 1000),  # Top-right mines
            (1000, 4000),  # Bottom-left mines
            (4000, 4000),  # Center mines
        ]
        
        # Track recently issued orders (prevent duplicates)
        self.last_commands = {}

    def execute_decision(self, decision: Dict[str, Any], current_gold: int) -> List[Dict[str, Any]]:
        """
        Convert decision into concrete commands
        
        Args:
            decision: Output from DecisionEngine.decide()
            current_gold: Current gold amount
        
        Returns:
            List of command dicts to send to server
        """
        commands = []
        
        # ====================================
        # STEP 1: Build units
        # ====================================
        
        build_attackers = decision.get("build_attackers", 0)
        build_collectors = decision.get("build_collectors", 0)
        
        for _ in range(build_attackers):
            cmd = self._create_build_attacker_command()
            if cmd:
                commands.append(cmd)
        
        for _ in range(build_collectors):
            cmd = self._create_build_collector_command()
            if cmd:
                commands.append(cmd)
        
        # ====================================
        # STEP 2: Move units to strategic locations
        # ====================================
        
        priority = decision.get("priority", "expand")
        aggression = decision.get("aggression", 0.0)
        
        move_commands = self._generate_movement_orders(priority, aggression)
        commands.extend(move_commands)
        
        # ====================================
        # STEP 3: Attack orders if aggressive
        # ====================================
        
        if aggression > 0.5:
            attack_commands = self._generate_attack_orders()
            commands.extend(attack_commands)
        
        return commands

    # ====================================
    # PRIVATE METHODS
    # ====================================

    def _create_build_attacker_command(self) -> Dict[str, Any]:
        """
        Create command to build an attacker unit
        
        Returns:
            Command dict or None if not possible
        """
        # Check if we have available unit slots
        if len(self.game_world.units) >= 50:  # Max units per player
            return None
        
        # Use JSON_Manager to generate command
        # For now, return the structure expected by network.py
        # The actual JSON encoding happens in network.py
        
        command = {
            "type": "build_unit",
            "unit_type": "attacker",
            "player_id": self.player_id
        }
        return command

    def _create_build_collector_command(self) -> Dict[str, Any]:
        """
        Create command to build a collector unit
        
        Returns:
            Command dict or None if not possible
        """
        if len(self.game_world.units) >= 50:
            return None
        
        command = {
            "type": "build_unit",
            "unit_type": "collector",
            "player_id": self.player_id
        }
        return command

    def _generate_movement_orders(self, priority: str, aggression: float) -> List[Dict[str, Any]]:
        """
        Generate movement orders for existing units based on priority
        
        Strategies:
        - "expand": Send collectors to nearest mines
        - "defend": Keep attackers near base
        - "attack": Move attackers toward enemy base
        
        Args:
            priority: Strategic priority
            aggression: Aggression level [0, 1]
        
        Returns:
            List of move commands
        """
        commands = []
        
        # Separate attackers and collectors
        attackers = []
        collectors = []
        
        for unit_id, unit in self.game_world.units.items():
            owner = self.game_world.get_owner_from_id(unit_id)
            if owner != self.player_id:
                continue
            
            if unit_id in self.attackers_range:
                attackers.append((unit_id, unit))
            elif unit_id in self.collectors_range:
                collectors.append((unit_id, unit))
        
        # ====================================
        # Move collectors (always expand)
        # ====================================
        
        for unit_id, unit in collectors:
            target = self._find_nearest_mining_location(unit.x, unit.y)
            if target:
                cmd = self._create_move_command(unit_id, target[0], target[1])
                commands.append(cmd)
        
        # ====================================
        # Move attackers (depends on priority)
        # ====================================
        
        if priority == "attack" or aggression > 0.5:
            # Move toward enemy base
            enemy_base = (300, 4700) if self.enemy_id == 1 else (4700, 300)
            for unit_id, unit in attackers:
                cmd = self._create_move_command(unit_id, enemy_base[0], enemy_base[1])
                commands.append(cmd)
        
        elif priority == "defend":
            # Keep near own base
            for unit_id, unit in attackers:
                base_x, base_y = self.player_base
                # Add some randomness around base
                offset_x = (hash((unit_id, "x")) % 400) - 200
                offset_y = (hash((unit_id, "y")) % 400) - 200
                target_x = max(0, min(5000, base_x + offset_x))
                target_y = max(0, min(5000, base_y + offset_y))
                cmd = self._create_move_command(unit_id, target_x, target_y)
                commands.append(cmd)
        
        else:  # "expand" - focus on collectors, keep attackers mobile
            # Spread attackers around for scouting
            for i, (unit_id, unit) in enumerate(attackers):
                scout_location = self.mining_locations[i % len(self.mining_locations)]
                cmd = self._create_move_command(unit_id, scout_location[0], scout_location[1])
                commands.append(cmd)
        
        return commands

    def _generate_attack_orders(self) -> List[Dict[str, Any]]:
        """
        Generate attack commands for nearest enemy units
        
        Returns:
            List of attack commands
        """
        commands = []
        
        # Find all attackers
        my_attackers = []
        for unit_id, unit in self.game_world.units.items():
            owner = self.game_world.get_owner_from_id(unit_id)
            if owner == self.player_id and unit_id in self.attackers_range:
                my_attackers.append((unit_id, unit))
        
        # Find all enemy units
        enemy_units = []
        for unit_id, unit in self.game_world.units.items():
            owner = self.game_world.get_owner_from_id(unit_id)
            if owner == self.enemy_id:
                enemy_units.append((unit_id, unit))
        
        if not enemy_units:
            return commands
        
        # Simple greedy assignment: each attacker targets nearest enemy
        for attacker_id, attacker_unit in my_attackers:
            nearest_enemy = min(
                enemy_units,
                key=lambda e: math.sqrt(
                    (attacker_unit.x - e[1].x)**2 + 
                    (attacker_unit.y - e[1].y)**2
                )
            )
            
            cmd = self._create_attack_command(attacker_id, nearest_enemy[0])
            commands.append(cmd)
        
        return commands

    def _find_nearest_mining_location(self, x: float, y: float) -> Tuple[float, float]:
        """
        Find nearest mining location to given position
        
        Args:
            x, y: Current position
        
        Returns:
            (target_x, target_y) tuple
        """
        if not self.mining_locations:
            return self.player_base
        
        nearest = min(
            self.mining_locations,
            key=lambda loc: math.sqrt((x - loc[0])**2 + (y - loc[1])**2)
        )
        return nearest

    def _create_move_command(self, unit_id: int, target_x: float, target_y: float) -> Dict[str, Any]:
        """
        Create a move command for a unit
        
        Args:
            unit_id: ID of unit to move
            target_x, target_y: Target position
        
        Returns:
            Command dict
        """
        command = {
            "type": "move",
            "unit_id": unit_id,
            "target_x": int(target_x),
            "target_y": int(target_y)
        }
        return command

    def _create_attack_command(self, attacker_id: int, target_id: int) -> Dict[str, Any]:
        """
        Create an attack command
        
        Args:
            attacker_id: ID of attacking unit
            target_id: ID of target unit
        
        Returns:
            Command dict
        """
        command = {
            "type": "attack",
            "attacker_id": attacker_id,
            "target_id": target_id
        }
        return command
