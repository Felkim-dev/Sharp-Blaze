# Decision Engine — Linear Programming Model

This document explains how the `DecisionEngine` class models the bot's strategic decision-making as a **Linear Programming (LP)** problem, solved using [SciPy's `linprog`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html) with the HiGHS backend.

---

## Table of Contents

1. [What is Linear Programming?](#what-is-linear-programming)
2. [Problem Overview](#problem-overview)
3. [Decision Variables](#decision-variables)
4. [Variable Bounds](#variable-bounds)
5. [Objective Function](#objective-function)
6. [Constraints](#constraints)
7. [Full LP Formulation](#full-lp-formulation)
8. [Post-Optimization Steps](#post-optimization-steps)
9. [Fallback Behavior](#fallback-behavior)
10. [Known Limitations](#known-limitations)

---

## What is Linear Programming?

Linear Programming is a mathematical method for finding the best outcome (maximum or minimum) of a **linear objective function**, subject to **linear constraints** (inequalities or equalities).

The standard form used by `scipy.optimize.linprog` is:

$$\text{minimize} \quad \mathbf{c}^T \mathbf{x}$$

$$\text{subject to} \quad A_{ub} \cdot \mathbf{x} \leq \mathbf{b}_{ub}$$

$$\quad \quad \quad \quad \quad \quad l_i \leq x_i \leq u_i \quad \forall i$$

Where:
- $\mathbf{c}$ is the cost vector (the objective coefficients)
- $\mathbf{x}$ is the vector of decision variables (what we want to find)
- $A_{ub}$ and $\mathbf{b}_{ub}$ define the inequality constraints
- $l_i$, $u_i$ are the lower and upper bounds for each variable

> **Important:** `linprog` always **minimizes**. To maximize a function $f(\mathbf{x})$, we minimize $-f(\mathbf{x})$.

---

## Problem Overview

At each game tick, the bot must decide:

- How many **attackers** to build
- How many **collectors** to build
- How **aggressive** to behave

These decisions depend on the current game state: how threatened the bot is, how efficiently it's gathering resources, and whether it holds a positional advantage. The LP formalizes this trade-off.

---

## Decision Variables

The solution vector $\mathbf{x} \in \mathbb{R}^3$ contains three variables:

| Index | Variable | Meaning |
|-------|----------|---------|
| $x_0$ | Attackers to build | Integer, continuous relaxation |
| $x_1$ | Collectors to build | Integer, continuous relaxation |
| $x_2$ | Aggression factor | Continuous value in $[0, 1]$ |

The LP treats $x_0$ and $x_1$ as **continuous** (real numbers). After the solver finishes, they are floored to integers — more on this in [Post-Optimization Steps](#post-optimization-steps).

---

## Variable Bounds

Before running the LP, each variable's feasible range is computed:

$$0 \leq x_0 \leq \min\!\left(\left\lfloor \frac{\text{gold}}{\text{ATTACKER\_COST}} \right\rfloor,\ \text{max\_units} - \text{total\_bot\_units}\right)$$

$$0 \leq x_1 \leq \min\!\left(\left\lfloor \frac{\text{gold}}{\text{COLLECTOR\_COST}} \right\rfloor,\ \text{max\_units} - \text{total\_bot\_units}\right)$$

$$0 \leq x_2 \leq 1$$

Each upper bound takes the **minimum** of two independent limits:

- **Gold limit:** how many units you can afford if you spent all gold on that type alone.
- **Slot limit:** how many unit slots are currently free.

These bounds act as *box constraints* — they restrict each variable independently before the constraints are applied. This reduces the solver's search space and prevents the solver from exploring obviously invalid regions.

> **Note:** Both $x_0$ and $x_1$ share the same slot limit independently, which means their combined upper bounds can exceed actual available slots. This is intentional — the shared slot budget is enforced jointly by Constraint 1.

---

## Objective Function

The bot wants to **maximize** a utility function that weighs three strategic goals:

$$U(\mathbf{x}) = \underbrace{w_t \cdot (\tau + 0.5)}_{\text{threat mitigation}} \cdot x_0 \;+\; \underbrace{w_r \cdot (1 - \rho)}_{\text{resource expansion}} \cdot x_1 \;+\; \underbrace{w_p \cdot \max(0,\ \pi)}_{\text{positional push}} \cdot x_2$$

Where:

| Symbol | Variable | Range |
|--------|----------|-------|
| $w_t$ | `threat_weight` | Config-defined |
| $w_r$ | `resource_weight` | Config-defined |
| $w_p$ | `position_weight` | Config-defined |
| $\tau$ | `threat_level` | $[0, 1]$ |
| $\rho$ | `resource_efficiency` | $[0, 1]$ |
| $\pi$ | `positional_advantage` | $(-\infty, +\infty)$ |

Since `linprog` minimizes, the objective vector passed to it is $\mathbf{c} = -\nabla U$:

$$c_0 = -w_t \cdot (\tau + 0.5)$$

$$c_1 = -w_r \cdot (1 - \rho)$$

$$c_2 = -w_p \cdot \max(0,\ \pi)$$

### Intuition behind each coefficient

**Attackers ($c_0$):**

The term $(\tau + 0.5)$ ensures $c_0$ is never zero, even at zero threat. The offset $+0.5$ means the bot always has *some* baseline incentive to build attackers. As threat increases, $c_0$ becomes more negative, pushing the solver to increase $x_0$.

**Collectors ($c_1$):**

The term $(1 - \rho)$ is inversely proportional to resource efficiency. When $\rho = 1.0$ (perfect efficiency), $c_1 = 0$ and the solver has no incentive to build collectors. When $\rho = 0.0$ (no efficiency), the incentive is maximum.

**Aggression ($c_2$):**

The $\max(0, \pi)$ clamps negative positional advantage to zero. If the bot is at a disadvantage ($\pi < 0$), $c_2 = 0$ and the solver will set $x_2 = 0$ (minimum aggression). If $\pi > 0$, $c_2 < 0$ and the solver pushes $x_2$ to its upper bound of $1$.

---

## Constraints

Constraints are expressed as rows in $A_{ub} \cdot \mathbf{x} \leq \mathbf{b}_{ub}$.

### Constraint 1 — Unit slot budget

Total units built cannot exceed available slots:

$$x_0 + x_1 \leq \max(1,\ \text{max\_units} - \text{total\_bot\_units})$$

In matrix row form: $[1,\ 1,\ 0]$

The $\max(1, \cdot)$ prevents the right-hand side from being zero or negative, which could make the system ill-conditioned even when the solver should simply build nothing.

### Constraint 2 — Gold budget

Total gold spent cannot exceed available funds (with an optional strategic spending cap):

$$\text{ATTACKER\_COST} \cdot x_0 + \text{COLLECTOR\_COST} \cdot x_1 \leq \min(\text{gold},\ \text{max\_gold\_spend})$$

In matrix row form: $[100,\ 50,\ 0]$

`max_gold_spend` is computed at initialization as:

$$\text{max\_gold\_spend} = \text{INITIAL\_GOLD} \times \text{gold\_spend\_ratio}$$

This allows the bot to deliberately reserve gold across turns instead of spending everything available.

### Constraint 3 — Minimum attackers under high threat (conditional)

Only active when $\tau > 0.7$. Forces the bot to build a minimum number of attackers:

$$x_0 \geq \min\!\left(\max(1,\ \lfloor \text{enemy\_attackers} \times 0.8 \rfloor),\ \text{max\_attackers\_buildable}\right)$$

Since `linprog` requires $\leq$ constraints, this is re-expressed by multiplying both sides by $-1$:

$$-x_0 \leq -\text{min\_attackers\_needed}$$

In matrix row form: $[-1,\ 0,\ 0]$

The right-hand side is capped at $-\text{max\_attackers\_buildable}$ to avoid demanding more attackers than the bot can physically build, which would make the system infeasible.

---

## Full LP Formulation

Putting it all together:

$$\text{minimize} \quad \mathbf{c}^T \mathbf{x} = c_0 x_0 + c_1 x_1 + c_2 x_2$$

$$\text{subject to:}$$

$$x_0 + x_1 \leq \max(1,\ S) \tag{slots}$$

$$100 x_0 + 50 x_1 \leq \min(G,\ G_{max}) \tag{gold}$$

$$-x_0 \leq -m \quad \text{(only if } \tau > 0.7\text{)} \tag{min attackers}$$

$$0 \leq x_0 \leq B_a, \quad 0 \leq x_1 \leq B_c, \quad 0 \leq x_2 \leq 1 \tag{bounds}$$

Where:
- $S = \text{max\_units} - \text{total\_bot\_units}$ (free slots)
- $G = \text{current\_gold}$
- $G_{max} = \text{max\_gold\_spend}$
- $m = \text{min\_attackers\_needed}$
- $B_a, B_c$ = upper bounds for attackers and collectors

---

## Post-Optimization Steps

### Integer rounding

The LP returns real-valued solutions. Since units must be whole numbers, results are floored:

$$x_0^* = \lfloor \hat{x}_0 \rfloor, \qquad x_1^* = \lfloor \hat{x}_1 \rfloor$$

`floor` is used instead of `round` because it is **budget-safe**: a value like $\hat{x}_0 = 2.9$ means the LP consumed enough gold budget for 2.9 attackers. Rounding up to 3 could violate the gold constraint in the integer solution. Flooring to 2 is always feasible.

### Aggression clipping

The aggression value is clipped to $[0, 1]$ to guard against floating-point artifacts from the solver:

$$x_2^* = \text{clip}(\hat{x}_2,\ 0.0,\ 1.0)$$

### Priority determination

After the LP, a simple rule cascade determines the strategic label:

```
threat_level > 0.6         → "defend"
resource_efficiency < 0.4  → "expand"
positional_advantage > 0.3 → "attack"
default                    → "expand" if collectors > attackers, else "attack"
```

This is independent of the LP — it's a human-readable label derived from the same game state metrics.

---

## Fallback Behavior

If the solver fails (infeasible system or numerical issues), the bot falls back to a conservative default:

```python
attackers_to_build  = 0
collectors_to_build = 1 if current_gold >= COLLECTOR_COST else 0
aggression          = 0.0
```

The most common failure scenario: Constraint 3 demands more attackers than the gold and slot constraints allow simultaneously, making the system infeasible. The code mitigates this by capping `min_attackers_needed` against `max_attackers_buildable`, but edge cases can still arise.

---

## Known Limitations

### Aggression is effectively binary

Because $x_2$ has no constraint linking it to $x_0$ or $x_1$, and $c_2 \leq 0$ always, the solver will push $x_2$ to either $0$ (when $\pi \leq 0$) or $1$ (when $\pi > 0$). It never settles at an intermediate value. The variable behaves as a boolean flag despite being modeled as continuous.

### Bounds are individually overestimated

Both $B_a$ and $B_c$ use the full slot count $S$ independently:

$$B_a = \min\!\left(\lfloor G / 100 \rfloor,\ S\right), \qquad B_c = \min\!\left(\lfloor G / 50 \rfloor,\ S\right)$$

This implies the bot could build $S$ attackers **and** $S$ collectors, which is impossible since slots are shared. Constraint 1 corrects this during solving, so the final result is still valid — but the bounds overestimate the individual feasible ranges.

### Missing aggression constraint (Constraint 4)

The intended constraint linking aggression to actual military strength:

$$x_2 \leq \frac{\text{bot\_attackers} + x_0}{\text{enemy\_attackers} + 1}$$

Can be linearized as:

$$-x_0 + (\text{enemy\_attackers} + 1) \cdot x_2 \leq \text{bot\_attackers}$$

This is a valid linear constraint (constant coefficient times a variable) and could be added as a row $[-1,\ 0,\ (\text{enemy\_attackers}+1)]$ in $A_{ub}$. It is currently left unimplemented, which means aggression is not properly bounded by military capacity.

---

## Dependencies

```
scipy >= 1.7.0   # linprog with HiGHS backend
numpy            # array operations
```
