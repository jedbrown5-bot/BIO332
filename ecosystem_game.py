"""
ECOSYSTEM MANAGEMENT: STATE-AND-TRANSITION ADVENTURE
====================================================

An educational simulation of grassland-shrubland dynamics for teaching:
  * State-and-transition models and threshold dynamics
  * Grass-fire feedback loops
  * Biomass accumulation and dominance effects on diversity
  * Compensatory / adaptive grazing dynamics
  * Invasion ecology under disturbance
  * Adaptive management with budget constraints

The model distinguishes grass COVER (structural) from grass BIOMASS
(standing crop + litter) and grass DIVERSITY (community richness). This
allows the system to express several real phenomena:

  * Productive but species-poor grasslands (high cover, high biomass,
    low diversity) - the *Eragrostis curvula* / *Themeda* unburnt-thatch
    syndrome: ecosystem function declines despite vegetation cover.
  * Compensatory grazing - light-moderate grazing on biomass-rich grass
    breaks dominance and lifts diversity.
  * Fire-mediated diversity recovery via thatch removal.
  * Overgrazing - heavy grazing on already-sparse grass degrades cover.

The player begins in a degraded, shrub-encroached state and has 30 years
to restore (or maintain) a functional grassland.
"""

from __future__ import annotations

import os
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional


# =====================================================================
# Domain types
# =====================================================================

class State(Enum):
    GRASSLAND = "GRASSLAND"
    TRANSITION = "TRANSITION"
    SHRUBLAND = "SHRUBLAND"


@dataclass
class Invasive:
    """A single invasive species population."""
    name: str
    effect: str          # grass_competitor | allelopathic | nitrogen_fixer
                         # | rapid_growth   | shade_creator
    strength: float      # 0.0 - 0.5


INVASIVE_POOL: list[tuple[str, str, tuple[float, float]]] = [
    ("African lovegrass", "grass_competitor", (0.10, 0.30)),
    ("Fireweed",          "allelopathic",     (0.10, 0.30)),
    ("African Olive",     "nitrogen_fixer",   (0.10, 0.30)),
    ("Buffel grass",      "rapid_growth",     (0.20, 0.40)),
    ("Blackberry",        "shade_creator",    (0.10, 0.25)),
]

GRAZABLE_INVASIVE_EFFECTS: set[str] = {
    "grass_competitor",
    "rapid_growth",
    "allelopathic",
    "shade_creator",
}


EVENT_TABLE: list[tuple[str, str, dict, float]] = [
    ("Drought",
     "A severe drought has affected the region.",
     {"grass": -15, "shrubs": -5, "ecosystem": -10}, 0.15),
    ("Wet Year",
     "Unusually high rainfall has created favorable growing conditions.",
     {"grass": 15, "shrubs": 10, "ecosystem": 10}, 0.15),
    ("Lightning Fire",
     "Lightning has started a natural wildfire in the ecosystem.",
     {"grass": -20, "shrubs": -25, "ecosystem": 5, "fire_reset": True}, 0.10),
    ("Disease Outbreak",
     "A plant pathogen is affecting vegetation in the ecosystem.",
     {"grass": -10, "shrubs": -10, "ecosystem": -15}, 0.10),
    ("Insect Outbreak",
     "An outbreak of plant-eating insects is affecting the ecosystem.",
     {"grass": -5, "shrubs": -15, "ecosystem": -10}, 0.10),
    ("Native Pollinator Boom",
     "Native pollinators are thriving, benefiting the ecosystem.",
     {"grass": 5, "shrubs": 5, "ecosystem": 15}, 0.10),
]


class EcosystemAdventure:

    GRASS_THRESHOLD = 40
    SHRUB_THRESHOLD = 60
    FIRE_INEFFECTIVE_AFTER = 7
    MAX_INVASIVES = 4
    GAME_LENGTH = 30

    STARTING_BUDGET = 80
    ANNUAL_BUDGET = 25

    def __init__(self) -> None:
        self.grass_cover: float = random.uniform(10, 25)
        self.shrub_density: float = random.uniform(60, 85)
        self.grazing_pressure: float = random.uniform(60, 80)
        self.ecosystem_function: float = random.uniform(30, 50)

        self.grass_biomass: float = self.grass_cover * random.uniform(0.6, 1.2)
        self.grass_diversity: float = min(
            60.0, self.grass_cover + random.uniform(20, 35)
        )

        self.current_state: State = State.SHRUBLAND
        self.year: int = 1
        self.years_since_fire: int = 2
        self.budget: int = self.STARTING_BUDGET
        self.invasive_species: list[Invasive] = []
        self.history: list[str] = []
        self.game_over: bool = False

        self.optimal_fire_interval: int = random.randint(3, 6)

        self.hard_mode: bool = False
        # Headless mode: suppress input() and print(); collect output in messages.
        self.headless: bool = False
        self.messages: list[str] = []

    def clear_screen(self) -> None:
        if not self.headless:
            os.system("cls" if os.name == "nt" else "clear")

    def pause(self, prompt: str = "\nPress Enter to continue...") -> None:
        if not self.headless:
            input(prompt)

    @staticmethod
    def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, x))

    def _log(self, *args, sep: str = " ") -> None:
        """Collect output. In terminal mode also prints immediately."""
        msg = sep.join(str(a) for a in args)
        self.messages.append(msg)
        if not self.headless:
            print(msg)

    def spend(self, amount: int) -> bool:
        if not self.hard_mode:
            return True
        if self.budget < amount:
            self._log(f"🚫 Not enough budget. Need ${amount}, have ${self.budget}.")
            return False
        self.budget -= amount
        return True

    @staticmethod
    def prompt_int(prompt: str, valid: range) -> Optional[int]:
        try:
            value = int(input(prompt))
        except ValueError:
            return None
        return value if value in valid else None

    def run_game(self) -> None:
        self._show_intro()

        while not self.game_over:
            self.display_status()
            advance = self.show_menu()
            if advance and not self.game_over:
                self.simulate_year()
                self._check_end_conditions()

        self._show_final_summary()

    def _show_intro(self) -> None:
        self.clear_screen()
        self._log("=" * 60)
        self._log("ECOSYSTEM MANAGEMENT: STATE AND TRANSITION ADVENTURE")
        self._log("=" * 60)
        self._log("\nWelcome! You are managing a grassland ecosystem that can")
        self._log("exist in multiple stable states. Your goal is to maintain")
        self._log("(or restore) a healthy grass-dominated ecosystem.")
        self._log("\nThe ecosystem has feedback loops, thresholds, and hysteresis:")
        self._log("  • GRASSLAND  - grass-dominated, frequent fires")
        self._log("  • TRANSITION - mixed and unstable")
        self._log("  • SHRUBLAND  - shrub-dominated, infrequent fires")
        self._log("\nThe grass community is tracked in three dimensions:")
        self._log("  • COVER     - how much ground is occupied by grass")
        self._log("  • BIOMASS   - standing crop + litter (the fuel load)")
        self._log("  • DIVERSITY - richness of the grass community")
        self._log("\nA productive grassland with no disturbance accumulates biomass,")
        self._log("which suppresses diversity and ultimately ecosystem function.")
        self._log("Disturbance (fire OR appropriate grazing) is required to keep")
        self._log("the system functional. Beware of crossing thresholds!")

        self._choose_difficulty()
        self.pause("\nPress Enter to begin your adventure...")

    def _choose_difficulty(self) -> None:
        self._log("\n" + "-" * 60)
        self._log("Choose difficulty:")
        self._log("  1. EASY - field observations and ecologist tips appear,")
        self._log("           and budget is not a constraint. Focus on the ecology.")
        self._log("  2. HARD - no hints, and you have a tight management budget")
        self._log(f"           (start: ${self.STARTING_BUDGET}, annual top-up: "
              f"${self.ANNUAL_BUDGET}). Spend carefully.")
        while True:
            choice = input("\nEnter 1 or 2: ").strip()
            if choice == "1":
                self.hard_mode = False
                self._log("\nEASY MODE: hints will appear, money is no object.")
                return
            if choice == "2":
                self.hard_mode = True
                self._log("\nHARD MODE: no hints, and resources are limited.")
                return
            self._log("Please enter 1 or 2.")

    def _check_end_conditions(self) -> None:
        if self.year >= self.GAME_LENGTH:
            self.game_over = True
        elif self.ecosystem_function <= 0:
            self._log("\n💀 ECOSYSTEM COLLAPSE: function has reached zero.")
            self._log("The land can no longer support the community that lived here.")
            self.pause()
            self.game_over = True

    def display_status(self) -> None:
        self.clear_screen()
        self._log("\n===== ECOSYSTEM STATUS =====")
        self._log(f"Year: {self.year} / {self.GAME_LENGTH}")
        self._log(f"Current State: {self.current_state.value}")

        bars = [
            ("Grass Cover       ", self.grass_cover,        "🌿",  5),
            ("Grass Biomass     ", self.grass_biomass,      "🌾",  5),
            ("Grass Diversity   ", self.grass_diversity,    "🌼", 10),
            ("Shrub Density     ", self.shrub_density,      "🌳",  5),
            ("Ecosystem Function", self.ecosystem_function, "🌱", 10),
            ("Grazing Pressure  ", self.grazing_pressure,   "🐄", 10),
        ]
        for label, value, emoji, divisor in bars:
            self._log(f"{label}: {value:5.1f}%  {emoji * int(value / divisor)}")

        self._log(f"Years since last fire: {self.years_since_fire}")
        if self.hard_mode:
            self._log(f"Budget: ${self.budget}")

        descriptions = {
            State.GRASSLAND:  "Grass-fire feedback maintains an open ecosystem.",
            State.TRANSITION: "Shifting between grass and shrub dominance — careful management is needed.",
            State.SHRUBLAND:  "Woody plants are locked in by positive feedbacks.",
        }
        self._log(f"\n{descriptions[self.current_state]}")

        if not self.hard_mode:
            hints = self._diagnostic_hints()
            if hints:
                self._log("\nField observations:")
                for hint in hints:
                    self._log(f"  • {hint}")

        if self.invasive_species:
            self._log("\n⚠️ ACTIVE INVASIVE SPECIES:")
            for i, sp in enumerate(self.invasive_species, 1):
                self._log(f"  {i}. {sp.name} — Impact: {int(sp.strength * 100)}%")

    def _diagnostic_hints(self) -> list[str]:
        hints: list[str] = []
        if self.grass_biomass > 70 and self.years_since_fire > 2:
            hints.append("Grass thatch is heavy — fire or moderate grazing would break dominance.")
        if self.grass_diversity < 30 and self.grass_cover > 30:
            hints.append("Grass community is species-poor — dominance effects are reducing function.")
        if self.grazing_pressure > 40 and self.grass_cover < 30:
            hints.append("Grazing is heavy on already-sparse grass — overgrazing risk.")
        if self.grass_biomass < 20 and self.years_since_fire >= self.optimal_fire_interval:
            hints.append("Fuel is too low for an effective burn — let biomass build first.")
        if self.grazing_pressure == 0 and self.grass_biomass > 65:
            hints.append("Total rest with high biomass is letting dominants exclude other species.")

        if self.shrub_density > self.SHRUB_THRESHOLD:
            hints.append("Shrubs are well established — they resprout after fire. "
                         "Mechanical or chemical removal first, then fire to maintain.")

        grazable_present = any(
            sp.effect in GRAZABLE_INVASIVE_EFFECTS
            for sp in self.invasive_species
        )
        if grazable_present and self.grass_biomass > 45:
            hints.append("Palatable grass invaders + high biomass — targeted grazing could "
                         "suppress them (see invasive species menu).")
        return hints

    def show_menu(self) -> bool:
        actions: dict[str, tuple[str, Callable[[], None], bool]] = {
            "1": ("Conduct prescribed burn",        self.conduct_prescribed_burn, True),
            "2": ("Adjust grazing pressure",        self.adjust_grazing,          True),
            "3": ("Remove shrubs",                  self.remove_shrubs,           True),
            "4": ("Reseed native grasses",          self.reseed_grasses,          True),
            "5": ("Manage invasive species",        self.manage_invasive_species, True),
            "6": ("Do nothing (advance one year)",  self.do_nothing,              True),
            "7": ("View ecosystem state history",   self.display_history,         False),
            "8": ("Exit game",                      self.exit_game,               False),
        }

        self._log("\n=== MANAGEMENT OPTIONS ===")
        for key, (label, _, _) in actions.items():
            self._log(f"{key}. {label}")

        choice = input("\nWhat would you like to do? ").strip()
        if choice in actions:
            _, handler, advances = actions[choice]
            handler()
            return advances and not self.game_over

        self._log("Invalid choice. Please try again.")
        self.pause()
        return False

    def do_nothing(self) -> None:
        self._log("\nYou chose to do nothing this year...")
        if not self.headless:
            time.sleep(1)
        shrub_growth = random.uniform(1, 3)
        grazing_drift = random.uniform(0, 2)
        eco_decline = random.uniform(0, 2) if self.ecosystem_function > 40 else 0

        self.shrub_density = self.clamp(self.shrub_density + shrub_growth)
        self.grazing_pressure = self.clamp(self.grazing_pressure + grazing_drift)
        self.ecosystem_function = self.clamp(self.ecosystem_function - eco_decline)

        self._log(f"Shrubs grew by {shrub_growth:.1f}% from lack of intervention.")
        self._log(f"Grazing pressure drifted up by {grazing_drift:.1f}%.")
        if eco_decline > 0:
            self._log(f"Ecosystem function declined by {eco_decline:.1f}%.")
        self.pause()

    def exit_game(self) -> None:
        self._log("\nExiting game. Thanks for playing!")
        self.game_over = True

    def display_history(self) -> None:
        self._log("\n=== ECOSYSTEM STATE HISTORY ===")
        if not self.history:
            self._log("No state transitions have occurred yet.")
        else:
            for event in self.history:
                self._log(event)
        self.pause()

    def conduct_prescribed_burn(self) -> None:
        if not self.spend(30):
            self.pause()
            return

        self._log("\n🔥 Conducting prescribed burn...")

        fuel = self.grass_biomass
        success_chance = (fuel / 100) * 0.85
        deviation = abs(self.years_since_fire - self.optimal_fire_interval)
        pre_fire_biomass = self.grass_biomass

        if fuel < 25:
            self._log("The burn was patchy — insufficient fuel to carry fire.")
            shrub_red = random.uniform(5, 15)
            eco_impact = random.uniform(-5, 5)
        elif self.years_since_fire < 2:
            self._log("Weak burn — fuel hadn't accumulated since the last fire.")
            shrub_red = random.uniform(10, 20)
            eco_impact = random.uniform(-10, 0)
        elif random.random() < success_chance:
            self._log("The prescribed burn was successful!")
            shrub_red = random.uniform(20, 40)
            eco_impact = random.uniform(5, 15)
            if self.current_state is State.TRANSITION:
                self._log("The fire effectively reduced woody vegetation.")
        else:
            self._log("The burn was only partially successful.")
            shrub_red = random.uniform(10, 25)
            eco_impact = random.uniform(-5, 10)

        if deviation == 0:
            self._log("\n✨ Perfect timing! Maximum ecological benefit.")
            shrub_red *= 1.5
            eco_impact += 15
            if self.invasive_species and random.random() < 0.3:
                removed = self.invasive_species.pop(
                    random.randrange(len(self.invasive_species))
                )
                self._log(f"The well-timed fire controlled {removed.name}!")
        elif deviation == 1:
            self._log("Good timing — solid ecological benefits.")
            shrub_red *= 1.2
            eco_impact += 5
        elif deviation >= 3:
            self._log("Suboptimal timing.")
            shrub_red *= 0.7
            eco_impact -= 10
            if random.random() < 0.3:
                self.introduce_invasive_species()

        density_factor, density_msg = self._fire_shrub_density_factor()
        shrub_red *= density_factor

        self.grass_biomass = self.clamp(self.grass_biomass * 0.15)
        self.shrub_density = self.clamp(self.shrub_density - shrub_red)
        self.grass_cover = self.clamp(self.grass_cover - random.uniform(5, 10))
        self.ecosystem_function = self.clamp(self.ecosystem_function + eco_impact)

        if density_msg:
            self._log(density_msg)

        if pre_fire_biomass > 60 and fuel >= 25 and self.years_since_fire >= 2:
            div_boost = random.uniform(3, 8)
            self.grass_diversity = self.clamp(self.grass_diversity + div_boost)
            self._log(f"  The fire reduced thatch and lifted diversity (+{div_boost:.1f}%).")
        elif pre_fire_biomass < 30 and fuel >= 25:
            div_loss = random.uniform(1, 4)
            self.grass_diversity = self.clamp(self.grass_diversity - div_loss)
            self._log(f"  Burning low-biomass grass hurt diversity (-{div_loss:.1f}%).")

        self.years_since_fire = 0

        self._log("Grasses will recover with vigour over the next few years.")
        sign = "+" if eco_impact >= 0 else ""
        self._log(f"Ecosystem function change: {sign}{eco_impact:.1f}%")

        if (not self.hard_mode
                and self.year > 5
                and deviation > 2
                and random.random() < 0.3):
            direction = "sooner" if self.years_since_fire > self.optimal_fire_interval else "later"
            self._log(f"\nA local ecologist hints the fire would have helped more "
                  f"if conducted {direction}.")

        self.pause()

    GRAZING_OPTIONS: list[tuple[str, int, int]] = [
        ("Remove all livestock (0%)", 0,  0),
        ("Light grazing (20%)",       0, 20),
        ("Moderate grazing (40%)",    0, 40),
        ("Heavy grazing (60%)",       0, 60),
        ("Very heavy grazing (80%)",  0, 80),
        ("Rotational grazing system", 25, 35),
    ]

    def adjust_grazing(self, choice: Optional[int] = None) -> None:
        if choice is None:
            self._log("\n=== ADJUST GRAZING PRESSURE ===")
            self._log(f"Current grazing pressure: {self.grazing_pressure:.1f}%\n")
            for i, (label, cost, _) in enumerate(self.GRAZING_OPTIONS, 1):
                cost_str = f"💰 ${cost}" if cost else "Free"
                self._log(f"{i}. {label} - {cost_str}")
            cancel = len(self.GRAZING_OPTIONS) + 1
            self._log(f"{cancel}. Cancel")
            choice = self.prompt_int(
                f"\nEnter your choice (1-{cancel}): ",
                range(1, cancel + 1),
            )
            if choice is None or choice == cancel:
                self._log("No changes made.")
                self.pause()
                return

        label, cost, intensity = self.GRAZING_OPTIONS[choice - 1]

        if cost and not self.spend(cost):
            self.pause()
            return

        if choice == 6:
            self._apply_rotational_grazing()
        else:
            self.grazing_pressure = intensity
            self._log(f"{label} applied.")

            if intensity == 0:
                self.grass_cover = self.clamp(self.grass_cover + random.uniform(2, 5))
            elif intensity >= 60:
                invasive_chance = 0.2 if intensity == 60 else 0.4
                if random.random() < invasive_chance:
                    self._log("Heavy grazing has favoured invasive species.")
                    self.introduce_invasive_species()

            if intensity >= 80:
                hit = random.uniform(5, 15)
                self.ecosystem_function = self.clamp(self.ecosystem_function - hit)
                self._log(f"Intense grazing reduced ecosystem function by {hit:.1f}%.")

        self.pause()

    def _apply_rotational_grazing(self) -> None:
        suitability = 0.3 + 0.5 * (self.grass_biomass / 100)
        roll = random.random()

        if roll < suitability * 0.6:
            self.grazing_pressure = 30
            grass_d = random.uniform(3, 10)
            div_d = random.uniform(4, 10)
            eco_d = random.uniform(8, 18)
            biomass_d = random.uniform(15, 30)
            self._log("Rotational grazing succeeded brilliantly!")
            self._log(f"  Cover +{grass_d:.1f}%, diversity +{div_d:.1f}%, "
                  f"function +{eco_d:.1f}%, biomass −{biomass_d:.1f}%.")
            self.grass_cover = self.clamp(self.grass_cover + grass_d)
            self.grass_diversity = self.clamp(self.grass_diversity + div_d)
            self.grass_biomass = self.clamp(self.grass_biomass - biomass_d)
            self.ecosystem_function = self.clamp(self.ecosystem_function + eco_d)
            if self.invasive_species and random.random() < 0.3:
                target = random.choice(self.invasive_species)
                target.strength *= 0.7
                self._log(f"  Strategic grazing weakened {target.name}.")
        elif roll < suitability:
            self.grazing_pressure = 35
            grass_d = random.uniform(0, 7)
            div_d = random.uniform(1, 4)
            eco_d = random.uniform(3, 10)
            self._log("Rotational grazing is working as expected.")
            self._log(f"  Cover +{grass_d:.1f}%, diversity +{div_d:.1f}%, "
                  f"function +{eco_d:.1f}%.")
            self.grass_cover = self.clamp(self.grass_cover + grass_d)
            self.grass_diversity = self.clamp(self.grass_diversity + div_d)
            self.ecosystem_function = self.clamp(self.ecosystem_function + eco_d)
        else:
            self.grazing_pressure = 45
            self._log("Rotational grazing faces implementation challenges.")
            if self.grass_biomass < 25:
                self._log("  Insufficient biomass — there isn't enough to redistribute.")
            self.grass_cover = self.clamp(self.grass_cover + random.uniform(-5, 5))
            self.ecosystem_function = self.clamp(
                self.ecosystem_function + random.uniform(-5, 8)
            )

    def remove_shrubs(self, choice: Optional[int] = None) -> None:
        if choice is None:
            self._log("\n=== SHRUB REMOVAL OPTIONS ===")
            self._log("1. Selective hand removal (Removes 10%)   - 💰 $10")
            self._log("2. Mechanical clearing   (Removes 30%)    - 💰 $25")
            self._log("3. Herbicide application (Removes 50%)    - 💰 $35")
            self._log("4. Integrated management approach         - 💰 $45")
            self._log("5. Cancel")
            choice = self.prompt_int("\nEnter your choice (1-5): ", range(1, 6))
            if choice is None or choice == 5:
                self._log("No changes made.")
                self.pause()
                return

        if choice == 1:
            if not self.spend(10):
                self.pause(); return
            self.shrub_density = self.clamp(self.shrub_density - 10)
            self._log("Selective removal completed. Shrub density reduced by 10%.")
            if self.invasive_species and random.random() < 0.2:
                removed = self.invasive_species.pop(
                    random.randrange(len(self.invasive_species))
                )
                self._log(f"Your careful work also removed some {removed.name}!")

        elif choice == 2:
            if not self.spend(25):
                self.pause(); return
            self.shrub_density = self.clamp(self.shrub_density - 30)
            if random.random() < 0.15:
                self._log("Soil disturbance has created opportunities for invasive species.")
                self.introduce_invasive_species()
            else:
                self._log("Mechanical clearing completed. Shrub density reduced by 30%.")

        elif choice == 3:
            if not self.spend(35):
                self.pause(); return
            self.shrub_density = self.clamp(self.shrub_density - 50)
            self.ecosystem_function = self.clamp(self.ecosystem_function - 20)
            self._log("Herbicide applied. Shrubs -50%, ecosystem function -20%.")
            if random.random() < 0.2:
                self._log("⚠️ The herbicide had unexpected consequences!")
                if random.random() < 0.5:
                    loss = random.uniform(10, 20)
                    self.grass_cover = self.clamp(self.grass_cover - loss)
                    self._log(f"Native grasses were also affected (-{loss:.1f}%).")
                else:
                    self._log("The disturbance opened the door to invaders.")
                    self.introduce_invasive_species()

        elif choice == 4:
            if not self.spend(45):
                self.pause(); return
            self._apply_integrated_shrub_management()

        self.pause()

    def _apply_integrated_shrub_management(self) -> None:
        self._log("Implementing integrated management approach...")
        roll = random.random()
        if roll > 0.7:
            shrub_red = random.uniform(40, 60)
            eco = random.uniform(5, 15)
            self._log(f"Very successful! Shrubs -{shrub_red:.1f}%, "
                  f"ecosystem function +{eco:.1f}%.")
            if self.invasive_species and random.random() < 0.4:
                removed = self.invasive_species.pop(
                    random.randrange(len(self.invasive_species))
                )
                self._log(f"The integrated approach also controlled {removed.name}!")
        elif roll > 0.3:
            shrub_red = random.uniform(20, 40)
            eco = random.uniform(-5, 10)
            sign = "+" if eco >= 0 else ""
            self._log(f"Moderately successful. Shrubs -{shrub_red:.1f}%, "
                  f"ecosystem function {sign}{eco:.1f}%.")
        else:
            shrub_red = random.uniform(5, 20)
            eco = random.uniform(-15, 0)
            self._log(f"Limited success. Shrubs -{shrub_red:.1f}%, "
                  f"ecosystem function {eco:.1f}%.")
            if random.random() < 0.3:
                self._log("The disturbance opened the door to invaders.")
                self.introduce_invasive_species()

        self.shrub_density = self.clamp(self.shrub_density - shrub_red)
        self.ecosystem_function = self.clamp(self.ecosystem_function + eco)

    RESEED_OPTIONS: list[tuple[str, int, int, float]] = [
        ("Minimal reseeding (+10%)",   15, 10, 0.0),
        ("Moderate reseeding (+25%)",  30, 25, 0.0),
        ("Intensive reseeding (+40%)", 50, 40, 0.2),
    ]

    def reseed_grasses(self, choice: Optional[int] = None) -> None:
        if choice is None:
            self._log("\n=== GRASS RESEEDING OPTIONS ===")
            for i, (label, cost, _, _) in enumerate(self.RESEED_OPTIONS, 1):
                self._log(f"{i}. {label} - 💰 ${cost}")
            self._log("4. Experimental native seed mix - 💰 $40")
            self._log("5. Cancel")
            choice = self.prompt_int("\nEnter your choice (1-5): ", range(1, 6))
            if choice is None or choice == 5:
                self._log("No changes made.")
                self.pause()
                return

        if choice in (1, 2, 3):
            label, cost, gain, risk = self.RESEED_OPTIONS[choice - 1]
            if not self.spend(cost):
                self.pause(); return
            self.grass_cover = self.clamp(self.grass_cover + gain)
            self.grass_diversity = self.clamp(
                self.grass_diversity + gain * 0.4
            )
            self._log(f"{label} completed. Grass cover increased by {gain}%.")
            if risk and random.random() < risk:
                self._log("⚠️ The seed mix appears to have been contaminated.")
                self.introduce_invasive_species()
        else:
            if not self.spend(40):
                self.pause(); return
            self._apply_experimental_seed_mix()

        self.pause()

    def _apply_experimental_seed_mix(self) -> None:
        self._log("Applying experimental native seed mix...")
        roll = random.random()
        if roll > 0.7:
            grass_d = random.uniform(40, 60)
            eco_d = random.uniform(10, 20)
            div_d = random.uniform(8, 15)
            self._log(f"Thrived! Cover +{grass_d:.1f}%, function +{eco_d:.1f}%, "
                  f"diversity +{div_d:.1f}%.")
            self.grass_cover = self.clamp(self.grass_cover + grass_d)
            self.grass_diversity = self.clamp(self.grass_diversity + div_d)
            self.ecosystem_function = self.clamp(self.ecosystem_function + eco_d)
            if self.invasive_species and random.random() < 0.4:
                removed = self.invasive_species.pop(
                    random.randrange(len(self.invasive_species))
                )
                self._log(f"The diverse native mix outcompeted {removed.name}!")
        elif roll > 0.3:
            grass_d = random.uniform(20, 40)
            div_d = random.uniform(3, 8)
            self._log(f"Established moderately. Cover +{grass_d:.1f}%, "
                  f"diversity +{div_d:.1f}%.")
            self.grass_cover = self.clamp(self.grass_cover + grass_d)
            self.grass_diversity = self.clamp(self.grass_diversity + div_d)
        else:
            grass_d = random.uniform(0, 15)
            self._log(f"Struggled to establish. Cover +{grass_d:.1f}%.")
            self.grass_cover = self.clamp(self.grass_cover + grass_d)
            if random.random() < 0.5:
                self._log("The failed seeding created opportunities for invaders.")
                self.introduce_invasive_species()

    def introduce_invasive_species(self) -> None:
        if len(self.invasive_species) >= self.MAX_INVASIVES:
            return
        name, effect, (lo, hi) = random.choice(INVASIVE_POOL)
        if any(sp.name == name for sp in self.invasive_species):
            return
        new = Invasive(name=name, effect=effect, strength=random.uniform(lo, hi))
        self.invasive_species.append(new)
        self._log(f"\n⚠️ ALERT: {new.name} has been detected in your ecosystem!")
        self._log("This invasive species will affect management outcomes.")
        self.pause()

    def apply_invasive_effects(self) -> None:
        effect_handlers = {
            "grass_competitor": self._effect_grass_competitor,
            "allelopathic":     self._effect_allelopathic,
            "nitrogen_fixer":   self._effect_nitrogen_fixer,
            "rapid_growth":     self._effect_rapid_growth,
            "shade_creator":    self._effect_shade_creator,
        }
        for sp in self.invasive_species:
            handler = effect_handlers.get(sp.effect)
            if handler:
                handler(sp)

    def _effect_grass_competitor(self, sp: Invasive) -> None:
        self.grass_biomass = self.clamp(self.grass_biomass + 6 * sp.strength)
        self.grass_diversity = self.clamp(self.grass_diversity - 7 * sp.strength)
        self._log(f"  • {sp.name} forms dominant tussocks — biomass climbs while "
              f"natives are excluded.")

    def _effect_allelopathic(self, sp: Invasive) -> None:
        self.grass_diversity = self.clamp(self.grass_diversity - 7 * sp.strength)
        self.grass_cover = self.clamp(self.grass_cover - 2 * sp.strength)
        self.ecosystem_function = self.clamp(self.ecosystem_function - 4 * sp.strength)
        self._log(f"  • {sp.name} releases allelopathic toxins — diversity falls "
              f"and livestock health suffers.")

    def _effect_nitrogen_fixer(self, sp: Invasive) -> None:
        self.shrub_density = self.clamp(self.shrub_density + 6 * sp.strength)
        self.grass_diversity = self.clamp(self.grass_diversity - 3 * sp.strength)
        self.ecosystem_function = self.clamp(self.ecosystem_function - 2 * sp.strength)
        self._log(f"  • {sp.name} is establishing woody dominance — soil N "
              f"enrichment favours further woody invasion.")

    def _effect_rapid_growth(self, sp: Invasive) -> None:
        self.grass_cover = self.clamp(self.grass_cover + 2 * sp.strength)
        self.grass_biomass = self.clamp(self.grass_biomass + 8 * sp.strength)
        self.grass_diversity = self.clamp(self.grass_diversity - 8 * sp.strength)
        self.ecosystem_function = self.clamp(self.ecosystem_function - 3 * sp.strength)
        self._log(f"  • {sp.name} is spreading laterally — biomass surges, "
              f"natives crowded out.")

    def _effect_shade_creator(self, sp: Invasive) -> None:
        self.shrub_density = self.clamp(self.shrub_density + 8 * sp.strength)
        self.grass_cover = self.clamp(self.grass_cover - 5 * sp.strength)
        self.grass_diversity = self.clamp(self.grass_diversity - 5 * sp.strength)
        self._log(f"  • {sp.name} is forming dense thickets — shrub cover "
              f"building rapidly.")

    def manage_invasive_species(
        self,
        choice: Optional[int] = None,
        target_idx: Optional[int] = None,
    ) -> None:
        if not self.invasive_species:
            self._log("\nThere are currently no invasive species in your ecosystem.")
            self.pause()
            return

        if choice is None:
            self._log("\n=== INVASIVE SPECIES MANAGEMENT ===")
            self._log("Currently present:")
            for i, sp in enumerate(self.invasive_species, 1):
                self._log(f"  {i}. {sp.name} — Impact: {int(sp.strength * 100)}%")
            self._log("\nManagement options:")
            self._log("1. Targeted removal             - 💰 $25  (60% success on chosen species)")
            self._log("2. Biocontrol introduction      - 💰 $40  (unpredictable)")
            self._log("3. Comprehensive management     - 💰 $50  (expensive but effective)")
            self._log("4. Targeted/conservation grazing- 💰 $30  (suppresses palatable invaders)")
            self._log("5. Cancel")
            choice = self.prompt_int("\nEnter your choice (1-5): ", range(1, 6))
            if choice is None or choice == 5:
                self._log("No changes made.")
                self.pause()
                return

        if choice == 1:
            if self.spend(25):
                self._targeted_removal(target_idx=target_idx)
        elif choice == 2:
            if self.spend(40):
                self._biocontrol()
        elif choice == 3:
            if self.spend(50):
                self._comprehensive_plan()
        elif choice == 4:
            grazable_present = any(
                sp.effect in GRAZABLE_INVASIVE_EFFECTS
                for sp in self.invasive_species
            )
            if not grazable_present:
                self._log("\nNone of your current invaders respond to grazing.")
                self._log("(Woody/unpalatable species need different management.)")
            elif self.spend(30):
                self._targeted_grazing()

        self.pause()

    def _targeted_removal(self, target_idx: Optional[int] = None) -> None:
        if target_idx is None:
            idx = self.prompt_int(
                f"Which species do you want to target? (1-{len(self.invasive_species)}): ",
                range(1, len(self.invasive_species) + 1),
            )
            if idx is None:
                self._log("Invalid selection.")
                return
        else:
            idx = target_idx

        target = self.invasive_species[idx - 1]
        self._log(f"Attempting to remove {target.name}...")

        if random.random() < 0.6:
            self.invasive_species.pop(idx - 1)
            self._log(f"Success! You've effectively controlled {target.name}.")
            self.ecosystem_function = self.clamp(
                self.ecosystem_function + random.uniform(5, 10)
            )
        else:
            self._log(f"Despite your efforts, {target.name} persists.")
            if random.random() < 0.3:
                target.strength = min(0.5, target.strength * 1.2)
                self._log("⚠️ The species has adapted and become more resilient!")

    def _biocontrol(self) -> None:
        self._log("Introducing biocontrol agents...")
        outcome = random.random()
        if outcome > 0.7:
            removed_count = min(len(self.invasive_species), random.randint(1, 2))
            for _ in range(removed_count):
                removed = self.invasive_species.pop(
                    random.randrange(len(self.invasive_species))
                )
                self._log(f"The biocontrol successfully managed {removed.name}!")
            self.ecosystem_function = self.clamp(
                self.ecosystem_function + random.uniform(5, 15)
            )
        elif outcome > 0.4:
            for sp in self.invasive_species:
                sp.strength *= 0.7
            self._log("Biocontrol agents have weakened, but not eliminated, invaders.")
        elif outcome > 0.1:
            self._log("The biocontrol agents failed to establish.")
        else:
            self._log("⚠️ The biocontrol agents themselves have become invasive!")
            self.ecosystem_function = self.clamp(
                self.ecosystem_function - random.uniform(10, 20)
            )
            self.invasive_species.append(Invasive(
                name="Invasive Biocontrol Agent",
                effect="rapid_growth",
                strength=random.uniform(0.2, 0.3),
            ))

    def _fire_shrub_density_factor(self) -> tuple[float, str]:
        if self.shrub_density < self.GRASS_THRESHOLD:
            return 1.0, ""
        if self.shrub_density < self.SHRUB_THRESHOLD:
            return 0.5, ("  Larger shrubs resprouted from lignotubers — "
                         "fire mainly killed seedlings and saplings.")
        return 0.2, ("  Mature shrubs survived by resprouting from "
                     "lignotubers and epicormic buds. Fire alone won't "
                     "reverse established shrubland.")

    def _comprehensive_plan(self) -> None:
        self._log("Implementing comprehensive invasive species management plan...")
        success_rate = min(0.9, 0.7 + (self.ecosystem_function / 200))

        removed_count = 0
        weakened_count = 0
        for sp in list(self.invasive_species):
            if random.random() < success_rate:
                self.invasive_species.remove(sp)
                removed_count += 1
            else:
                sp.strength *= 0.5
                weakened_count += 1

        if removed_count:
            self._log(f"Successfully removed {removed_count} invasive species!")
        if weakened_count:
            self._log(f"Weakened the impact of {weakened_count} invasive species.")

        boost = random.uniform(5, 15)
        self.ecosystem_function = self.clamp(self.ecosystem_function + boost)
        self._log(f"The comprehensive approach improved ecosystem function by {boost:.1f}%.")

    def _targeted_grazing(self) -> None:
        type_effectiveness = {
            "rapid_growth":     (0.30, 0.50),
            "allelopathic":     (0.20, 0.35),
            "grass_competitor": (0.15, 0.35),
            "shade_creator":    (0.15, 0.30),
        }

        grazable = [sp for sp in self.invasive_species
                    if sp.effect in GRAZABLE_INVASIVE_EFFECTS]
        non_grazable = [sp for sp in self.invasive_species
                        if sp.effect not in GRAZABLE_INVASIVE_EFFECTS]

        self._log("\nDeploying livestock for targeted weed control...")

        eliminated: list[Invasive] = []
        for sp in grazable:
            lo, hi = type_effectiveness[sp.effect]
            reduction = random.uniform(lo, hi)
            old_strength = sp.strength
            sp.strength *= (1 - reduction)
            self._log(f"  • {sp.name}: impact {int(old_strength * 100)}% "
                  f"→ {int(sp.strength * 100)}%")
            if sp.strength < 0.05:
                eliminated.append(sp)

        for sp in eliminated:
            self.invasive_species.remove(sp)
            self._log(f"    ✓ {sp.name} effectively controlled!")

        biomass_removed = random.uniform(8, 18)
        self.grass_biomass = self.clamp(self.grass_biomass - biomass_removed)
        self._log(f"  Grass biomass −{biomass_removed:.1f}% (eaten by livestock).")

        if self.grass_cover > 30 and self.grass_diversity > 25:
            div_boost = random.uniform(2, 5)
            self.grass_diversity = self.clamp(self.grass_diversity + div_boost)
            self._log(f"  Native species responding to released niches "
                  f"(+{div_boost:.1f}% diversity).")

        if non_grazable:
            names = ", ".join(sp.name for sp in non_grazable)
            self._log(f"  Unaffected (woody/unpalatable): {names}.")

    def simulate_year(self) -> None:
        self.year += 1
        self.years_since_fire += 1
        if self.hard_mode:
            self.budget += self.ANNUAL_BUDGET

        old = (self.grass_cover, self.grass_biomass, self.grass_diversity,
               self.shrub_density, self.ecosystem_function)

        self._apply_grazing_impact()
        self._apply_competition()
        self._apply_shrub_growth()
        self._apply_function_feedback()

        if self.invasive_species:
            self.apply_invasive_effects()

        self._normalise_cover()

        self._apply_biomass_dynamics()
        self._apply_diversity_dynamics()

        self._update_function_trend()

        labels = ["Grass cover       ", "Grass biomass     ", "Grass diversity   ",
                  "Shrub density     ", "Ecosystem function"]
        new = (self.grass_cover, self.grass_biomass, self.grass_diversity,
               self.shrub_density, self.ecosystem_function)
        self._log(f"\nYear {self.year} changes:")
        for label, before, after in zip(labels, old, new):
            self._log(f"  {label}: {before:5.1f}% → {after:5.1f}%")
        self._log(f"  Years since fire:   {self.years_since_fire}")
        if self.hard_mode:
            self._log(f"  (Annual budget +${self.ANNUAL_BUDGET}, now ${self.budget})")

        self._maybe_introduce_invasive()
        self._random_event()
        self._update_state()

    def _apply_grazing_impact(self) -> None:
        p = self.grazing_pressure

        biomass_removed = 0.35 * p
        self.grass_biomass = self.clamp(self.grass_biomass - biomass_removed)

        if p == 0:
            cover_loss = 0.0
        elif self.grass_biomass > 50 and p <= 40:
            cover_loss = 0.02 * p
        elif self.grass_cover < 30 and p > 40:
            cover_loss = 0.25 * p
        elif p <= 20:
            cover_loss = 0.0
        elif p <= 40:
            cover_loss = 0.05 * p
        elif p <= 60:
            cover_loss = 0.10 * p
        else:
            cover_loss = 0.18 * p
        self.grass_cover = self.clamp(self.grass_cover - cover_loss)

        if 20 < p <= 40 and self.grass_biomass > 55:
            self.grass_diversity = self.clamp(
                self.grass_diversity + random.uniform(1.0, 2.5)
            )
        elif p == 0 and self.grass_biomass > 65:
            self.grass_diversity = self.clamp(
                self.grass_diversity - random.uniform(0.5, 1.5)
            )
        elif p > 70:
            self.grass_diversity = self.clamp(
                self.grass_diversity - random.uniform(1.0, 3.0)
            )

    def _apply_biomass_dynamics(self) -> None:
        ceiling = min(100, self.grass_cover * 1.2)
        if self.grass_biomass < ceiling:
            gap = ceiling - self.grass_biomass
            self.grass_biomass += 0.4 * gap
        else:
            excess = self.grass_biomass - ceiling
            self.grass_biomass -= 0.6 * excess
        self.grass_biomass = self.clamp(self.grass_biomass)

    def _apply_diversity_dynamics(self) -> None:
        if self.grass_biomass > 65 and self.years_since_fire > 2:
            years_factor = min(2.0, self.years_since_fire / 3)
            self.grass_diversity = self.clamp(
                self.grass_diversity - 0.5 * years_factor
            )

        if (20 <= self.grass_cover <= 85
                and self.grass_biomass < 70
                and self.grazing_pressure <= 50):
            self.grass_diversity = self.clamp(
                self.grass_diversity + random.uniform(0.5, 1.5)
            )

        invasive_load = sum(sp.strength for sp in self.invasive_species)
        if invasive_load > 0.3:
            self.grass_diversity = self.clamp(
                self.grass_diversity - invasive_load * 1.5
            )

        SEEDBANK_BUFFER = 30
        cover_ceiling = min(100.0, self.grass_cover + SEEDBANK_BUFFER)
        if self.grass_diversity > cover_ceiling:
            excess = self.grass_diversity - cover_ceiling
            self.grass_diversity -= min(2.0, 0.3 * excess)

        if self.grass_cover < 5:
            self.grass_diversity = max(0.0, self.grass_diversity - 1.5)

        self.grass_diversity = self.clamp(self.grass_diversity)

    def _apply_competition(self) -> None:
        if self.shrub_density > 40:
            factor = (self.shrub_density - 30) / 100
            self.grass_cover = self.clamp(self.grass_cover - 5 * factor)

    def _apply_shrub_growth(self) -> None:
        bare = max(0, 100 - (self.grass_cover + self.shrub_density))
        growth = 2 + (bare / 20)
        if self.shrub_density > 30:
            growth += self.shrub_density / 10
        self.shrub_density = self.clamp(self.shrub_density + growth)

    def _apply_function_feedback(self) -> None:
        if self.ecosystem_function < 50:
            loss = min(1.5, (50 - self.ecosystem_function) / 20)
            self.grass_cover = self.clamp(self.grass_cover - loss)

    def _normalise_cover(self) -> None:
        total = self.grass_cover + self.shrub_density
        if total > 100:
            excess = (total - 100) / 2
            self.grass_cover -= excess
            self.shrub_density -= excess

    def _update_function_trend(self) -> None:
        diversity_signal = (self.grass_diversity - 50) / 25

        biomass_penalty = max(0.0, self.grass_biomass - 70) / 15

        good_cover = (
            40 < self.grass_cover < 85
            and self.shrub_density < 40
            and self.grazing_pressure < 60
        )
        bad_cover = self.grass_cover < 15 or self.shrub_density > 70

        if good_cover:
            base = 1.0
        elif bad_cover:
            base = -1.2
        else:
            base = -0.3

        delta = base + 0.6 * diversity_signal - biomass_penalty
        delta += random.uniform(-0.3, 0.3)

        self.ecosystem_function = self.clamp(self.ecosystem_function + delta)

    def _maybe_introduce_invasive(self) -> None:
        if random.random() < 0.15 and len(self.invasive_species) < self.MAX_INVASIVES:
            self.introduce_invasive_species()

    def _random_event(self) -> None:
        if random.random() > 0.2:
            return

        r = random.random()
        cumulative = 0.0
        chosen = None
        for name, desc, effects, weight in EVENT_TABLE:
            cumulative += weight
            if r <= cumulative:
                chosen = (name, desc, effects)
                break
        if chosen is None:
            return

        name, desc, effects = chosen
        self._log(f"\n⚠️ ECOLOGICAL EVENT: {name} ⚠️")
        self._log(desc)

        is_lightning_fire = (name == "Lightning Fire")
        density_msg_to_print = ""

        for key, label in (("grass", "Grass cover"),
                           ("shrubs", "Shrub density"),
                           ("ecosystem", "Ecosystem function")):
            if key not in effects:
                continue
            attr = {"grass": "grass_cover",
                    "shrubs": "shrub_density",
                    "ecosystem": "ecosystem_function"}[key]
            old_val = getattr(self, attr)

            if key == "shrubs" and is_lightning_fire:
                factor, density_msg_to_print = self._fire_shrub_density_factor()
                delta = effects[key] * factor
            else:
                delta = effects[key]

            new_val = self.clamp(old_val + delta)
            setattr(self, attr, new_val)
            self._log(f"  {label}: {old_val:.1f}% → {new_val:.1f}%")

        if density_msg_to_print:
            self._log(density_msg_to_print)

        if effects.get("fire_reset"):
            self.years_since_fire = 0
            self.grass_biomass = self.clamp(self.grass_biomass * 0.2)
            self._log("  Fire history reset; biomass consumed.")

        if name == "Drought":
            self.grass_biomass = self.clamp(self.grass_biomass - random.uniform(10, 20))
        elif name == "Wet Year":
            self.grass_biomass = self.clamp(self.grass_biomass + random.uniform(8, 15))

        if name == "Drought" and random.random() < 0.3:
            self._log("The drought has favoured invasive species.")
            self.introduce_invasive_species()
        elif name == "Wet Year" and self.invasive_species and random.random() < 0.3:
            target = random.choice(self.invasive_species)
            target.strength = min(0.5, target.strength * 1.3)
            self._log(f"The wet conditions caused a {target.name} population boom!")

        self.pause()

    def _update_state(self) -> None:
        previous = self.current_state

        if self.grass_cover < self.GRASS_THRESHOLD and self.shrub_density > self.SHRUB_THRESHOLD:
            self.current_state = State.SHRUBLAND
        elif self.grass_cover > 60 and self.shrub_density < 30:
            self.current_state = State.GRASSLAND
        elif self.grass_cover < self.GRASS_THRESHOLD or self.shrub_density > 40:
            self.current_state = State.TRANSITION

        if previous is not self.current_state:
            self.history.append(
                f"Year {self.year}: Transition from {previous.value} to {self.current_state.value}"
            )
            if self.current_state is State.SHRUBLAND:
                self._log("\n🌳 THRESHOLD CROSSED: shrub-dominated state reached.")
                self._log("This will be difficult to reverse without significant intervention.")
                self.pause()
            elif self.current_state is State.GRASSLAND:
                self._log("\n🌿 THRESHOLD CROSSED: ecosystem has recovered to grassland.")
                self.pause()

    def _show_final_summary(self) -> None:
        self.clear_screen()

        if self.year >= self.GAME_LENGTH:
            self._log("\n🎉 Congratulations! You've managed the ecosystem for 30 years!\n")
        elif self.ecosystem_function <= 0:
            self._log("\n💀 GAME OVER: the ecosystem collapsed under your watch.\n")

        endings = {
            State.GRASSLAND: ("You've maintained a healthy GRASSLAND ecosystem!",
                              "The balance between grass and fire has created a sustainable environment."),
            State.TRANSITION: ("Your ecosystem is in a TRANSITION state.",
                               "It's neither fully grass nor fully shrub dominated."),
            State.SHRUBLAND:  ("Your ecosystem has become a SHRUBLAND.",
                               "Woody plants have taken over what was once grassland."),
        }
        line1, line2 = endings[self.current_state]
        self._log("Final ecosystem state:")
        self._log(line1)
        self._log(line2)

        self._log("\nFINAL STATISTICS:")
        self._log(f"  Final grass cover:        {self.grass_cover:.1f}%")
        self._log(f"  Final grass biomass:      {self.grass_biomass:.1f}%")
        self._log(f"  Final grass diversity:    {self.grass_diversity:.1f}%")
        self._log(f"  Final shrub density:      {self.shrub_density:.1f}%")
        self._log(f"  Final ecosystem function: {self.ecosystem_function:.1f}%")
        self._log(f"  State transitions:        {len(self.history)}")
        if self.invasive_species:
            self._log(f"  Invasive species present: {len(self.invasive_species)}")
        else:
            self._log("  No invasive species present - excellent management!")

        score = self._compute_score()
        self._log(f"\nFINAL SCORE: {score}/200")
        self._log(f"RATING: {self._rating(score)}")

        self._log(f"\nFun fact: Your ecosystem's optimal fire interval was every "
              f"{self.optimal_fire_interval} years.")
        self._log("\nTHANK YOU FOR PLAYING!")
        self.pause("\nPress Enter to exit...")

    def _compute_score(self) -> int:
        if self.ecosystem_function <= 0:
            return 0
        score = 0.0
        score += self.grass_cover * 0.4
        score += self.grass_diversity * 0.6
        score += (100 - abs(self.grass_biomass - 50)) * 0.2
        score += (100 - self.shrub_density) * 0.3
        score += self.ecosystem_function * 0.7
        score -= len(self.invasive_species) * 20
        if self.current_state is State.GRASSLAND:
            score += 50
        elif self.current_state is State.TRANSITION:
            score += 25
        return int(max(0, min(200, score)))

    @staticmethod
    def _rating(score: int) -> str:
        if score == 0:    return "Ecosystem Collapse - The land is no longer functional."
        if score >= 160:  return "Master Ecologist - Your management was exceptional!"
        if score >= 120:  return "Skilled Land Manager - Your ecosystem is in good condition."
        if score >= 80:   return "Competent Steward - You maintained a functional ecosystem."
        return "Novice Manager - Ecological management is challenging!"


if __name__ == "__main__":
    game = EcosystemAdventure()
    game.run_game()
