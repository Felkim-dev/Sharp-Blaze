from typing import Dict, Any, List, Tuple
import math
from utils.json import JSON_Manager
from .game_config_loader import GameConfigLoader


class UnitCommander:
    """
    Generates concrete unit commands from strategic decisions.
    
    Responsibilities:
    - Build units (Attacker/Collector) based on decision
    - Move units to strategic locations
    - Queue attack orders when needed
    
    Commands are sent via network.py using JSON protocol
    """

    def __init__(self, game_world, network, player_id: int, difficulty: str = "MEDIUM"):
        """
        Initialize unit commander
        
        Args:
            game_world: GameWorld instance (for unit positions, terrain)
            network: Network instance (for sending commands)
            player_id: 1 or 2, which player is bot
            difficulty: EASY, MEDIUM or HARD difficulty profile
        """
        self.game_world = game_world
        self.network = network
        self.player_id = player_id
        self.difficulty = difficulty
        self.enemy_id = 2 if player_id == 1 else 1

        self.config_loader = GameConfigLoader()
        self.difficulty_params = self.config_loader.get_difficulty_params(difficulty) or {}
        self.command_budget = {
            "EASY": 4,
            "MEDIUM": 7,
            "HARD": 10,
        }.get(difficulty, 6)
        self.attack_group_cap = {
            "EASY": 1,
            "MEDIUM": 3,
            "HARD": 5,
        }.get(difficulty, 2)
        self.scout_group_cap = {
            "EASY": 1,
            "MEDIUM": 2,
            "HARD": 4,
        }.get(difficulty, 1)
        
        # Unit ID ranges
        if player_id == 1:
            self.attackers_range = range(1000, 3000)
            self.collectors_range = range(3000, 5000)
            self.player_base = (300, 4700)
            # Enemy base structure IDs (Player 2 structures: 5000-5999)
            self.enemy_base_id_range = range(5000, 6000)
        else:
            self.attackers_range = range(6000, 8000)
            self.collectors_range = range(8000, 10000)
            self.player_base = (4700, 300)
            # Enemy base structure IDs (Player 1 structures: 0-999)
            self.enemy_base_id_range = range(0, 1000)
        
        self.mining_locations = [
            (3500, 3500),  # Center mines (Resource 10000)
            (2100, 2900),  # Upper-left mines (Resource 10001)
            (2900, 2100),  # Upper-left mines (Resource 10002)
            (1500, 1500),  # Upper-left corner mines (Resource 10003)
        ]
        
        # Threshold: if collector is within this distance of a mine, send it back to base
        self.mine_arrival_threshold = 400  # world pixels
        # Threshold: if collector is close to base, send it to mine again
        self.base_arrival_threshold = 400  # world pixels
        
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
        remaining_budget = self.command_budget
        
        # ====================================
        # STEP 1: Build units
        # ====================================
        
        build_attackers = decision.get("build_attackers", 0)
        build_collectors = decision.get("build_collectors", 0)
        if build_attackers + build_collectors > remaining_budget:
            preferred_attackers = min(build_attackers, remaining_budget)
            remaining_budget -= preferred_attackers
            build_collectors = min(build_collectors, remaining_budget)
            build_attackers = preferred_attackers
        
        for _ in range(build_attackers):
            cmd = self._create_build_attacker_command()
            if cmd:
                commands.append(cmd)
                remaining_budget -= 1
                if remaining_budget <= 0:
                    return commands
        
        for _ in range(build_collectors):
            cmd = self._create_build_collector_command()
            if cmd:
                commands.append(cmd)
                remaining_budget -= 1
                if remaining_budget <= 0:
                    return commands
        
        # ====================================
        # STEP 2: Move units to strategic locations
        # ====================================
        
        priority = decision.get("priority", "expand")
        aggression = decision.get("aggression", 0.0)
        army_balance = decision.get("army_balance", 0.0)
        threat_level = decision.get("threat_level", 0.5)
        
        move_commands = self._generate_movement_orders(priority, aggression, army_balance, threat_level)
        for cmd in move_commands:
            commands.append(cmd)
            remaining_budget -= 1
            if remaining_budget <= 0:
                return commands
        
        # ====================================
        # STEP 3: Attack orders if aggressive
        # ====================================
        
        if aggression > 0.45 or priority == "attack":
            attack_commands = self._generate_attack_orders(priority, aggression, army_balance, threat_level)
            for cmd in attack_commands:
                commands.append(cmd)
                remaining_budget -= 1
                if remaining_budget <= 0:
                    return commands
        
        return commands

    # ====================================
    # PRIVATE METHODS
    # ====================================

    def _create_build_attacker_command(self) -> Dict[str, Any]:
        """
        Create command to build an attacker unit
        
        Uses JSON_Manager.get_unit_attacker() to generate TCP-compatible command
        
        Returns:
            Command dict (TCP protocol format) or None if not possible
        """
        # Check if we have available unit slots
        if len(self.game_world.units) >= 50:  # Max units per player
            return None
        
        # Use JSON_Manager to generate proper TCP command
        # Returns: {"type": "BUY_UNIT", "payload": {"unit_type": "Attacker", "quantity": 1}}
        command = JSON_Manager.get_unit_attacker()
        return command

    def _create_build_collector_command(self) -> Dict[str, Any]:
        """
        Create command to build a collector unit
        
        Uses JSON_Manager.get_unit_recolectors() to generate TCP-compatible command
        
        Returns:
            Command dict (TCP protocol format) or None if not possible
        """
        if len(self.game_world.units) >= 50:
            return None
        
        # Use JSON_Manager to generate proper TCP command
        # Returns: {"type": "BUY_UNIT", "payload": {"unit_type": "Collector", "quantity": 1}}
        command = JSON_Manager.get_unit_recolectors()
        return command

    def _generate_movement_orders(self, priority: str, aggression: float,
                                  army_balance: float, threat_level: float) -> List[Dict[str, Any]]:
        """
        Generate movement orders for existing units based on priority
        
        Strategies:
        - "expand": Send collectors to nearest mines
        - "defend": Keep attackers near base
        - "attack": Move attackers toward enemy base
        
        Args:
            priority: Strategic priority ("attack", "defend", "expand")
            aggression: Aggression level [0, 1]
        
        Returns:
            List of move commands (TCP protocol format via JSON_Manager)
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
        # Move collectors — explicit state machine per unit
        # States: "to_mine"  → heading to nearest mine to collect
        #         "to_base"  → heading to own base to deposit
        # Transition only happens when the unit actually arrives (within threshold).
        # ====================================
        
        base_x, base_y = self.player_base
        collector_limit = len(collectors) if self.difficulty != "EASY" else min(len(collectors), 3)
        for unit_id, unit in collectors[:collector_limit]:
            dist_to_base = math.sqrt((unit.x - base_x)**2 + (unit.y - base_y)**2)
            nearest_mine = self._find_nearest_mining_location(unit.x, unit.y)
            dist_to_mine = math.sqrt((unit.x - nearest_mine[0])**2 + (unit.y - nearest_mine[1])**2) if nearest_mine else float('inf')

            if dist_to_mine <= self.mine_arrival_threshold:
                # Collector arrived near mine → send it back to base to deposit
                cmd = self._create_move_command(unit_id, base_x, base_y)
                commands.append(cmd)
            elif dist_to_base <= self.base_arrival_threshold:
                # Collector arrived at base (deposited) → send it to mine again
                if nearest_mine:
                    cmd = self._create_move_command(unit_id, nearest_mine[0], nearest_mine[1])
                    commands.append(cmd)
            else:
                # In transit → keep going to the nearest mine
                if nearest_mine:
                    cmd = self._create_move_command(unit_id, nearest_mine[0], nearest_mine[1])
                    commands.append(cmd)
        
        # ====================================
        # Move attackers (depends on priority)
        # ====================================
        
        attack_force = self._select_attack_force(attackers, priority, aggression, army_balance, threat_level)

        if priority == "attack" or aggression > 0.5:
            # Move toward enemy base
            enemy_base = (300, 4700) if self.enemy_id == 1 else (4700, 300)
            for unit_id, unit in attack_force:
                cmd = self._create_move_command(unit_id, enemy_base[0], enemy_base[1])
                commands.append(cmd)
        
        elif priority == "defend":
            # Keep near own base
            for unit_id, unit in attack_force:
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
            scout_force = attack_force[:self.scout_group_cap]
            for i, (unit_id, unit) in enumerate(scout_force):
                scout_location = self.mining_locations[i % len(self.mining_locations)]
                cmd = self._create_move_command(unit_id, scout_location[0], scout_location[1])
                commands.append(cmd)
        
        return commands

    def _get_enemy_base_id(self) -> int:
        """
        Find the enemy base structure ID from game_world.structures.
        
        Returns:
            Structure ID of the enemy base, or None if not found.
        """
        for struct_id in self.game_world.structures:
            if struct_id in self.enemy_base_id_range:
                return struct_id
        return None

    def _select_attack_force(self, attackers, priority: str, aggression: float,
                             army_balance: float, threat_level: float):
        if not attackers:
            return []

        if self.difficulty == "EASY":
            cap = 1 if priority != "attack" else 2
        elif self.difficulty == "MEDIUM":
            cap = self.attack_group_cap if aggression <= 0.6 else min(len(attackers), self.attack_group_cap + 1)
        else:
            cap = self.attack_group_cap
            if priority == "attack" and army_balance > 0:
                cap += 1
            if threat_level < 0.35 and aggression > 0.7:
                cap += 1

        cap = max(1, min(len(attackers), cap))
        return sorted(attackers, key=lambda item: item[0])[:cap]

    def _generate_attack_orders(self, priority: str, aggression: float,
                                army_balance: float, threat_level: float) -> List[Dict[str, Any]]:
        """
        Generate attack commands for nearest enemy units or the enemy base.
        
        Priority:
        1. Attack enemy units if any exist
        2. Attack enemy base directly if no enemy units are present
        
        Returns:
            List of attack commands
        """
        commands = []
        
        # Find all own attackers
        my_attackers = []
        for unit_id, unit in self.game_world.units.items():
            owner = self.game_world.get_owner_from_id(unit_id)
            if owner == self.player_id and unit_id in self.attackers_range:
                my_attackers.append((unit_id, unit))
        
        if not my_attackers:
            return commands

        attack_force = self._select_attack_force(my_attackers, priority, aggression, army_balance, threat_level)
        if not attack_force:
            return commands

        # Find all enemy units
        enemy_units = []
        for unit_id, unit in self.game_world.units.items():
            owner = self.game_world.get_owner_from_id(unit_id)
            if owner == self.enemy_id:
                enemy_units.append((unit_id, unit))
        
        if enemy_units:
            # Priority 1: Attack nearest enemy unit
            for attacker_id, attacker_unit in attack_force:
                nearest_enemy = min(
                    enemy_units,
                    key=lambda e: math.sqrt(
                        (attacker_unit.x - e[1].x)**2 + 
                        (attacker_unit.y - e[1].y)**2
                    )
                )
                cmd = self._create_attack_command(attacker_id, nearest_enemy[0])
                commands.append(cmd)
        else:
            # Priority 2: No enemy units → attack enemy base structure directly
            enemy_base_id = self._get_enemy_base_id()
            if enemy_base_id is not None:
                for attacker_id, _ in attack_force:
                    cmd = self._create_attack_command(attacker_id, enemy_base_id)
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
        
        Uses JSON_Manager.get_moveorder() to generate TCP-compatible command
        
        Args:
            unit_id: ID of unit to move
            target_x, target_y: Target position (world coordinates)
        
        Returns:
            Command dict (TCP protocol format)
            Format: {"type": "MOVE_ORDER", "payload": {"unit_id": ..., "target_x": ..., "target_y": ...}}
        """
        # Convert world coordinates to grid indexes expected by the server
        # Server expects target_x/target_y in [0..99] (grid indices), not world pixels.
        cell_size = 50
        grid_x = int(target_x // cell_size)
        grid_y = int(target_y // cell_size)

        # Clamp to valid grid range
        grid_x = max(0, min(99, grid_x))
        grid_y = max(0, min(99, grid_y))

        # Use JSON_Manager to generate proper TCP command with grid indices
        command = JSON_Manager.get_moveorder(unit_id, grid_x, grid_y)
        return command

    def _create_attack_command(self, attacker_id: int, target_id: int) -> Dict[str, Any]:
        """
        Create an attack command
        
        Uses JSON_Manager.attack() to generate TCP-compatible command
        
        Args:
            attacker_id: ID of attacking unit
            target_id: ID of target unit
        
        Returns:
            Command dict (TCP protocol format)
            Format: {"type": "ATTACK", "payload": {"attacker_id": ..., "target_id": ...}}
        """
        # Use JSON_Manager to generate proper TCP command
        command = JSON_Manager.attack(target_id, attacker_id)
        return command
