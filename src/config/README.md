# Sharp-Blaze Configuration Files

This directory contains all configuration files for the game mechanics and AI bot parameters.

## Files

### `combat_stats.json`
**Purpose**: Core game mechanics configuration
- Unit stats: HP, damage, range, cooldown
- Grid parameters: cell size, obstacle padding
- Base stats and player definitions
- **Managed by**: Game Design team

### `bot_ai_config.json`
**Purpose**: AI Bot behavior and Simplex optimization parameters
- Difficulty levels: EASY, MEDIUM, HARD
- Bot decision-making weights
- Simplex constraints for optimization
- **Managed by**: AI/ML team

---

## Bot Difficulty Levels

### EASY
- **Target**: ~56% win rate vs human players
- **Behavior**: Cautious, defensive, resource-focused
- **Decision Cycle**: 1000ms (slower reactions)
- **Aggression**: 0.3 (Low - prefers safety)

**Key Parameters**:
- `threat_weight: 0.2` - Low defense priority
- `resource_weight: 0.5` - High gold gathering focus
- `position_weight: 0.3` - Moderate map control

### MEDIUM
- **Target**: ~75% win rate vs human players
- **Behavior**: Balanced between offense and defense
- **Decision Cycle**: 700ms (moderate reactions)
- **Aggression**: 0.6 (Medium - opportunistic)

**Key Parameters**:
- `threat_weight: 0.4` - Balanced defense
- `resource_weight: 0.4` - Balanced gold gathering
- `position_weight: 0.2` - Less map control focus

### HARD
- **Target**: ~90% win rate vs human players
- **Behavior**: Aggressive, offensive-first strategy
- **Decision Cycle**: 500ms (rapid reactions)
- **Aggression**: 0.9 (High - always attacking)

**Key Parameters**:
- `threat_weight: 0.5` - High defense priority (but still offensive)
- `resource_weight: 0.3` - Lower gold focus
- `position_weight: 0.2` - Minimal map control focus

---