# OpenCode — Sprint 6 Briefing

**PRD**: PRD-013 Persona Depth & UX Overhaul
**Branch**: `feat/PRD-013-persona-depth`
**Priority**: P0 — **WAVE 1** (send immediately, Codex depends on your output)

---

## Your Task: Indian Name Generation + Human-Readable Persona IDs

### 1. Create `src/generation/names.py`

Build a deterministic Indian name generator:

```python
"""Indian first name pools for persona ID generation."""

from __future__ import annotations

FEMALE_NAMES: tuple[str, ...] = (
    "Priya", "Ananya", "Meera", "Kavita", "Sunita", "Deepa", "Asha", "Ritu",
    "Neha", "Pooja", "Swati", "Anjali", "Divya", "Shruti", "Nisha", "Rekha",
    "Shalini", "Padma", "Lakshmi", "Geeta", "Rani", "Seema", "Vandana", "Preeti",
    "Archana", "Jyoti", "Rashmi", "Usha", "Kiran", "Manju", "Sarita", "Radha",
    "Sneha", "Bhavna", "Manisha", "Shweta", "Aishwarya", "Tanvi", "Pallavi", "Aparna",
    "Smita", "Rina", "Amita", "Varsha", "Chitra", "Suman", "Tara", "Veena",
    "Yamini", "Nandini", "Harini", "Revathi", "Lavanya", "Madhavi", "Ishita", "Kriti",
    "Aditi", "Sakshi", "Ritika", "Trisha", "Arti", "Bhavani", "Durga", "Hema",
    "Janaki", "Kamala", "Lata", "Malini", "Nirmala", "Pushpa", "Rohini", "Saroja",
    "Uma", "Vijaya", "Zara", "Farhana", "Ayesha", "Sana", "Noor", "Rukhsar",
    "Fatima", "Shabnam", "Nasreen", "Tabassum", "Zainab", "Amreen", "Hina", "Salma",
    "Dilshad", "Mehreen", "Parveen", "Rubina", "Shahnaz", "Tahira", "Yasmin", "Zubaida",
    "Bina", "Champa", "Devi", "Ganga", "Indira", "Kusum",
)

MALE_NAMES: tuple[str, ...] = (
    "Rahul", "Amit", "Vikram", "Suresh", "Rajesh", "Arun", "Sanjay", "Manoj",
    "Ravi", "Ashok", "Deepak", "Vinod", "Anil", "Prakash", "Dinesh", "Ramesh",
    "Mukesh", "Naresh", "Satish", "Girish", "Harish", "Mahesh", "Ganesh", "Sunil",
    "Vivek", "Ajay", "Vijay", "Nitin", "Rohit", "Sachin", "Tushar", "Varun",
    "Arjun", "Dev", "Hari", "Ishaan", "Jai", "Karthik", "Mohan", "Naveen",
    "Om", "Pranav", "Rohan", "Siddharth", "Tarun", "Uday", "Yash", "Akash",
    "Bharat", "Chandan", "Dhruv", "Gaurav", "Himanshu", "Kunal", "Lalit", "Manish",
    "Nikhil", "Pankaj", "Rakesh", "Sameer", "Tanmay", "Umesh", "Vishal", "Abhishek",
    "Farhan", "Imran", "Junaid", "Khalid", "Irfan", "Nadeem", "Rashid", "Salman",
    "Tariq", "Wasim", "Zaheer", "Aamir", "Danish", "Faisal", "Hamid", "Javed",
    "Karim", "Mansoor", "Nasir", "Owais", "Qasim", "Raza", "Shahid", "Usman",
    "Baldev", "Charan", "Darshan", "Gurpreet", "Harjot", "Jaspreet", "Manpreet",
    "Paramjit", "Ranjit", "Simran", "Tejinder", "Amarjit",
)


def generate_persona_name(
    *,
    gender: str,
    index: int,
    seed: int,
) -> str:
    """Deterministic first name selection from Indian name pools.

    Args:
        gender: "female" or "male" (maps to Mom/Dad).
        index: Persona index in generation order.
        seed: Population seed for reproducibility.

    Returns:
        An Indian first name string.
    """
    pool = FEMALE_NAMES if gender == "female" else MALE_NAMES
    # Deterministic but shuffled selection — avoids alphabetical clustering
    hash_val = hash((seed, index, gender)) % len(pool)
    return pool[hash_val]


def generate_persona_id(
    *,
    name: str,
    city_name: str,
    gender: str,
    parent_age: int,
    index: int,
) -> str:
    """Human-readable persona ID.

    Format: Name-City-Mom/Dad-Age (e.g. Priya-Mumbai-Mom-32).
    Appends index suffix if needed for uniqueness.
    """
    role = "Mom" if gender == "female" else "Dad"
    # Clean city name — remove spaces, use title case
    city = city_name.split()[0].title()  # "New Delhi" → "New"
    # For multi-word cities, join without spaces
    city = city_name.replace(" ", "").title() if " " in city_name else city
    base = f"{name}-{city}-{role}-{parent_age}"
    return base
```

### 2. Update `src/taxonomy/schema.py`

Add `display_name` field to the `Persona` class:

```python
display_name: str | None = None
```

This should be an optional field (not frozen — it's generated post-construction). Add it near the `narrative` field.

### 3. Update `src/generation/population.py`

In `PopulationGenerator.generate()`, replace the ID generation:

**Current (line ~289)**:
```python
"id": f"{population_id}-t1-{i:05d}",
```

**New**:
```python
from src.generation.names import generate_persona_name, generate_persona_id

name = generate_persona_name(
    gender=persona.demographics.parent_gender,
    index=i,
    seed=seed,
)
pid = generate_persona_id(
    name=name,
    city_name=persona.demographics.city_name,
    gender=persona.demographics.parent_gender,
    parent_age=persona.demographics.parent_age,
    index=i,
)
# ... then in the update dict:
"id": pid,
"display_name": name,
```

**Handle duplicates**: After generating all IDs, scan for duplicates and append `-2`, `-3` etc. to later occurrences.

**Remove Tier 2 ID re-generation**: The tier2 selection in lines 316-327 currently regenerates IDs. Keep the original human-readable ID — just update `tier` to `"deep"`.

### 4. Tests

**File**: `tests/unit/test_names.py` (new)

```python
def test_generate_persona_name_deterministic():
    """Same seed+index+gender always produces same name."""

def test_generate_persona_name_male_vs_female():
    """Male and female names come from different pools."""

def test_generate_persona_id_format():
    """ID follows Name-City-Role-Age format."""

def test_duplicate_id_resolution():
    """Population generation handles duplicate IDs."""
```

---

## Standards
- `from __future__ import annotations`
- Constants from `src.constants` where applicable
- Name pools must include Muslim, Sikh, South Indian names — not just Hindi/North Indian
- `ConfigDict(extra="forbid")` on any new models
- Target: 4+ new tests

## Run
```bash
uv run pytest tests/ -x -q
uv run ruff check src/generation/names.py tests/unit/test_names.py
```
