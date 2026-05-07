"""Bot AI logic that makes decisions using the Simplex optimizer"""

import time
from typing import Optional
from ia.bot_player import BotPlayer
from ia.simplex_optimizer import SimplexOptimizer


class BotAI:
    """AI controller for the bot player that makes strategic decisions"""

    def __init__(
        self,
        bot_player: BotPlayer,
        session_id: int,
        player_id: int,
        local_player_id: str,
        enemy_player_id: str,
        difficulty: str = "normal"
    ):
        """Initialize bot AI
        
        Args:
            bot_player (BotPlayer): Connection handler
            session_id (int): Game session ID
            player_id (int): Global player ID (1 or 2)
            local_player_id (str): Local player name/ID
            enemy_player_id (str): Enemy player name/ID
            difficulty (str): AI difficulty level
        """
        self.bot_player = bot_player
        self.session_id = session_id
        self.player_id = player_id
        self.local_player_id = local_player_id
        self.enemy_player_id = enemy_player_id
        
        # AI components
        self.optimizer = SimplexOptimizer(difficulty)
        self.difficulty = difficulty
        
        # Timing
        self.game_start_time = time.time()
        self.last_decision_time = 0
        self.decision_interval_ms = 1000  # Make decisions every 1 second
        self.last_tactical_update_ms = 0
        self.tactical_interval_ms = 1200
        self.last_wave_update_ms = 0
        self.wave_interval_ms = 3500
        self.wave_index = 0
        self.shop_runner_id = None
        self.initial_attack_delay_ms = 0  # No delay before attacking
        
        # Decision history (for logging)
        self.decision_history = []
        self.purchase_count = {"Collector": 0, "Attacker": 0}
        
        # State caching
        self.last_state = None
        self.assigned_collectors = set()

    def _get_wave_waypoints(self):
        # Waypoints from each spawn corner toward center and enemy base.
        if self.player_id == 2:
            return [(85, 15), (70, 30), (55, 45), (35, 60), (20, 75), (10, 90)]
        return [(15, 85), (30, 70), (45, 55), (60, 40), (75, 25), (90, 10)]

    def update(self) -> Optional[str]:
        """Called every game tick to update AI and make decisions
        
        Returns:
            str: Decision made ("Collector", "Attacker", or None)
        """
        
        current_time_ms = (time.time() - self.game_start_time) * 1000
        
        # Check if enough time passed since last decision
        if not self.optimizer.should_make_decision(current_time_ms):
            return None
        
        # Get current game state from bot player
        state = self.bot_player.get_state()
        
        if not state["connected"]:
            print("[BOT-AI] Not connected, skipping decision")
            return None
        
        self.last_state = state
        game_time_seconds = current_time_ms / 1000.0
        
        # Extract metrics
        available_gold = state["gold"]
        num_own_collectors = self._count_units(state["own_units"], "Collector")
        num_own_attackers = self._count_units(state["own_units"], "Attacker")
        num_enemy_units = len(state["enemy_units"])
        
        # Compute optimal decision
        decision = None
        if state.get("shop_authorized", False):
            decision = self.optimizer.compute_optimal_purchase(
                available_gold,
                num_own_collectors,
                num_own_attackers,
                num_enemy_units,
                game_time_seconds
            )
        
        # Log decision
        self._log_decision(
            decision,
            available_gold,
            num_own_collectors,
            num_own_attackers,
            num_enemy_units,
            game_time_seconds
        )
        
        # Execute decision
        if decision:
            success = self._execute_decision(decision)
            if success:
                self.purchase_count[decision] += 1
                print(f"[BOT-AI] Purchased {decision} (Total: {self.purchase_count})")
                self._run_tactical_actions(state, current_time_ms)
                return decision

        self._run_tactical_actions(state, current_time_ms)
        
        return None

    def _run_tactical_actions(self, state: dict, current_time_ms: float):
        if current_time_ms - self.last_tactical_update_ms < self.tactical_interval_ms:
            return
        self.last_tactical_update_ms = current_time_ms

        self._move_unit_to_shop_for_authorization(state)
        self._issue_collector_resource_orders(state, current_time_ms)
        
        if current_time_ms > self.initial_attack_delay_ms:
            self._issue_attack_orders(state)
        else:
            print(f"[BOT-AI] Attack delayed. Waiting {int((self.initial_attack_delay_ms - current_time_ms) / 1000)}s...")

    def _move_unit_to_shop_for_authorization(self, state: dict):
        if state.get("shop_authorized", False):
            self.shop_runner_id = None
            return

        shop_cell = state.get("shop_cell", (50, 50))
        own_units = state["own_units"]

        if self.shop_runner_id is None or self.shop_runner_id not in own_units:
            for unit_id, unit in own_units.items():
                if unit.get("type") == "Collector":
                    self.shop_runner_id = unit_id
                    break

            if self.shop_runner_id is None and own_units:
                self.shop_runner_id = next(iter(own_units.keys()))

        if self.shop_runner_id is not None:
            if self.bot_player.send_move_unit(self.shop_runner_id, shop_cell[0], shop_cell[1]):
                print(f"[BOT-AI] Moving unit {self.shop_runner_id} to shop for authorization")

    def _issue_collector_resource_orders(self, state: dict, current_time_ms: float):
        collectors = [
            unit_id
            for unit_id, unit in state["own_units"].items()
            if unit.get("type") == "Collector"
        ]
        if not collectors:
            return

        if not state.get("shop_authorized", False) and self.shop_runner_id is not None:
            collectors = [unit_id for unit_id in collectors if unit_id != self.shop_runner_id]
            if not collectors:
                return

        if not hasattr(self, "collector_states"):
            self.collector_states = {}

        # Clean up dead collectors
        own_units = state["own_units"]
        self.collector_states = {cid: cstate for cid, cstate in self.collector_states.items() if cid in own_units}

        resource_cells = state.get("resource_cells", [(70, 70), (42, 58), (58, 42), (30, 30)])
        
        base_structs = self.bot_player.structures
        if base_structs:
            base_pos = list(base_structs.values())[0]
            base_cell = (int(base_pos["x"] / 50), int(base_pos["y"] / 50))
        else:
            base_cell = (75, 75)

        TRIP_TIME_MS = 14000  # 14 seconds one-way trip
        issued = 0

        for idx, collector_id in enumerate(collectors):
            if collector_id not in self.collector_states:
                # Initial assignment
                target = resource_cells[idx % len(resource_cells)]
                self.collector_states[collector_id] = {
                    "state": "mining",
                    "target_node": target,
                    "last_order_time": current_time_ms
                }
                if self.bot_player.send_move_unit(collector_id, target[0], target[1]):
                    issued += 1
                continue
            
            c_state = self.collector_states[collector_id]
            time_since_order = current_time_ms - c_state["last_order_time"]

            if c_state["state"] == "mining" and time_since_order > TRIP_TIME_MS:
                c_state["state"] = "returning"
                c_state["last_order_time"] = current_time_ms
                if self.bot_player.send_move_unit(collector_id, base_cell[0], base_cell[1]):
                    issued += 1
            elif c_state["state"] == "returning" and time_since_order > TRIP_TIME_MS:
                c_state["state"] = "mining"
                c_state["last_order_time"] = current_time_ms
                target = c_state["target_node"]
                if self.bot_player.send_move_unit(collector_id, target[0], target[1]):
                    issued += 1

        if issued > 0:
            print(f"[BOT-AI] Collector resource orders sent: {issued}")

    def _pick_priority_target(self, enemy_units: dict):
        if not enemy_units:
            return None

        # Priority 1: enemy attackers
        attacker_targets = [
            entity_id
            for entity_id, unit in enemy_units.items()
            if unit.get("type") == "Attacker"
        ]
        if attacker_targets:
            return attacker_targets[0]

        # Priority 2: enemy collectors
        collector_targets = [
            entity_id
            for entity_id, unit in enemy_units.items()
            if unit.get("type") == "Collector"
        ]
        if collector_targets:
            return collector_targets[0]

        # Priority 3: enemy base
        base_targets = [
            entity_id
            for entity_id, unit in enemy_units.items()
            if unit.get("type") == "Structure" and (entity_id == 0 or entity_id == 5000)
        ]
        if base_targets:
            return base_targets[0]

        return next(iter(enemy_units.keys()))

    def _issue_attack_orders(self, state: dict):
        blacklisted = set(state.get("blacklisted_attackers", []))
        attacker_ids = [
            unit_id
            for unit_id, unit in state["own_units"].items()
            if unit.get("type") == "Attacker" and unit_id not in blacklisted and unit.get("hp", 1) > 0
        ]
        if not attacker_ids or not state["enemy_units"]:
            return

        target_id = self._pick_priority_target(state["enemy_units"])
        if target_id is None:
            return
        issued = 0
        for attacker_id in attacker_ids:
            if self.bot_player.send_attack(attacker_id, target_id):
                issued += 1

        if issued > 0:
            print(f"[BOT-AI] Attack orders sent: {issued} attackers -> target {target_id}")

    def _issue_wave_movement_orders(self, state: dict, current_time_ms: float):
        if current_time_ms - self.last_wave_update_ms < self.wave_interval_ms:
            return
        self.last_wave_update_ms = current_time_ms

        own_units = state["own_units"]
        wave_waypoints = self._get_wave_waypoints()
        if not wave_waypoints:
            return
        target_wave = wave_waypoints[self.wave_index % len(wave_waypoints)]
        self.wave_index += 1

        blacklisted = set(state.get("blacklisted_attackers", []))
        attacker_ids = [
            unit_id
            for unit_id, unit in own_units.items()
            if unit.get("type") == "Attacker" and unit_id not in blacklisted and unit.get("hp", 1) > 0
        ]

        move_count = 0
        for idx, attacker_id in enumerate(attacker_ids):
            offset = (idx % 5) - 2
            tx = max(0, min(99, target_wave[0] + offset))
            ty = max(0, min(99, target_wave[1] + offset))
            if self.bot_player.send_move_unit(attacker_id, tx, ty):
                move_count += 1

        if move_count > 0:
            print(
                f"[BOT-AI] Wave movement orders sent: {move_count} "
                f"towards waypoint {target_wave}"
            )

    def _count_units(self, units_dict: dict, unit_type: str) -> int:
        """Count units of a specific type
        
        Args:
            units_dict (dict): Dictionary of units
            unit_type (str): Unit type to count
            
        Returns:
            int: Number of units of that type
        """
        return sum(1 for u in units_dict.values() if u.get("type") == unit_type)

    def _execute_decision(self, decision: str) -> bool:
        """Execute a purchasing decision
        
        Args:
            decision (str): "Collector" or "Attacker"
            
        Returns:
            bool: True if executed successfully
        """
        return self.bot_player.send_buy_unit(decision, quantity=1)

    def _log_decision(
        self,
        decision: Optional[str],
        available_gold: int,
        num_own_collectors: int,
        num_own_attackers: int,
        num_enemy_units: int,
        game_time_seconds: float
    ):
        """Log decision for debugging
        
        Args:
            decision: Decision made
            available_gold: Gold available
            num_own_collectors: Collector count
            num_own_attackers: Attacker count
            num_enemy_units: Enemy unit count
            game_time_seconds: Game time
        """
        action_str = decision if decision else "WAIT"
        strategy = self.optimizer.get_strategy_info(game_time_seconds)
        
        log_entry = {
            "time": game_time_seconds,
            "strategy": strategy,
            "gold": available_gold,
            "collectors": num_own_collectors,
            "attackers": num_own_attackers,
            "enemy_units": num_enemy_units,
            "decision": action_str
        }
        
        self.decision_history.append(log_entry)
        
        # Print verbose output
        print(
            f"[BOT-AI] T={game_time_seconds:.1f}s | "
            f"Gold={available_gold} | "
            f"Own: {num_own_collectors}C {num_own_attackers}A | "
            f"Enemy: {num_enemy_units} | "
            f"Decision: {action_str} | "
            f"Phase: {strategy}"
        )

    def is_game_running(self) -> bool:
        """Check if bot is still in an active game
        
        Returns:
            bool: True if connected and game running
        """
        return self.bot_player.connected

    def get_statistics(self) -> dict:
        """Get AI statistics for debugging
        
        Returns:
            dict: Statistics about bot decisions
        """
        total_decisions = len(self.decision_history)
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "difficulty": self.difficulty,
            "total_decisions": total_decisions,
            "collectors_purchased": self.purchase_count["Collector"],
            "attackers_purchased": self.purchase_count["Attacker"],
            "decision_history": self.decision_history[-20:]  # Last 20 decisions
        }

    def get_current_state_summary(self) -> str:
        """Get human-readable summary of current state
        
        Returns:
            str: Formatted state summary
        """
        if not self.last_state:
            return "[BOT-AI] No state available"
        
        state = self.last_state
        game_time = (time.time() - self.game_start_time)
        collectors = self._count_units(state["own_units"], "Collector")
        attackers = self._count_units(state["own_units"], "Attacker")
        
        return (
            f"[BOT-AI State] "
            f"Time: {game_time:.1f}s | "
            f"Gold: {state['gold']} | "
            f"Units: {collectors}C+{attackers}A | "
            f"Enemy: {len(state['enemy_units'])} | "
            f"Connected: {state['connected']}"
        )
