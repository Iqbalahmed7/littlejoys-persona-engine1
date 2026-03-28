"""Indian name pools and deterministic persona name/id generation.

Used for human-readable persona IDs in the simulation population generator.
"""

from __future__ import annotations

import hashlib

FEMALE_NAMES: tuple[str, ...] = (
    "Priya",
    "Ananya",
    "Meera",
    "Kavita",
    "Sunita",
    "Deepa",
    "Asha",
    "Ritu",
    "Neha",
    "Pooja",
    "Swati",
    "Anjali",
    "Divya",
    "Shruti",
    "Nisha",
    "Rekha",
    "Shalini",
    "Padma",
    "Lakshmi",
    "Geeta",
    "Rani",
    "Seema",
    "Vandana",
    "Preeti",
    "Archana",
    "Jyoti",
    "Rashmi",
    "Usha",
    "Kiran",
    "Manju",
    "Sarita",
    "Radha",
    "Sneha",
    "Bhavna",
    "Manisha",
    "Shweta",
    "Aishwarya",
    "Tanvi",
    "Pallavi",
    "Aparna",
    "Smita",
    "Rina",
    "Amita",
    "Varsha",
    "Chitra",
    "Suman",
    "Tara",
    "Veena",
    "Yamini",
    "Nandini",
    "Harini",
    "Revathi",
    "Lavanya",
    "Madhavi",
    "Ishita",
    "Kriti",
    "Aditi",
    "Sakshi",
    "Ritika",
    "Trisha",
    "Arti",
    "Bhavani",
    "Durga",
    "Hema",
    "Janaki",
    "Kamala",
    "Lata",
    "Malini",
    "Nirmala",
    "Pushpa",
    "Rohini",
    "Saroja",
    "Uma",
    "Vijaya",
    "Zara",
    "Farhana",
    "Ayesha",
    "Sana",
    "Noor",
    "Rukhsar",
    "Fatima",
    "Shabnam",
    "Nasreen",
    "Tabassum",
    "Zainab",
    "Amreen",
    "Hina",
    "Salma",
    "Dilshad",
    "Mehreen",
    "Parveen",
    "Rubina",
    "Shahnaz",
    "Tahira",
    "Yasmin",
    "Zubaida",
    "Bina",
    "Champa",
    "Devi",
    "Ganga",
    "Indira",
    "Kusum",
)


MALE_NAMES: tuple[str, ...] = (
    "Rahul",
    "Amit",
    "Vikram",
    "Suresh",
    "Rajesh",
    "Arun",
    "Sanjay",
    "Manoj",
    "Ravi",
    "Ashok",
    "Deepak",
    "Vinod",
    "Anil",
    "Prakash",
    "Dinesh",
    "Ramesh",
    "Mukesh",
    "Naresh",
    "Satish",
    "Girish",
    "Harish",
    "Mahesh",
    "Ganesh",
    "Sunil",
    "Vivek",
    "Ajay",
    "Vijay",
    "Nitin",
    "Rohit",
    "Sachin",
    "Tushar",
    "Varun",
    "Arjun",
    "Dev",
    "Hari",
    "Ishaan",
    "Jai",
    "Karthik",
    "Mohan",
    "Naveen",
    "Om",
    "Pranav",
    "Rohan",
    "Siddharth",
    "Tarun",
    "Uday",
    "Yash",
    "Akash",
    "Bharat",
    "Chandan",
    "Dhruv",
    "Gaurav",
    "Himanshu",
    "Kunal",
    "Lalit",
    "Manish",
    "Nikhil",
    "Pankaj",
    "Rakesh",
    "Sameer",
    "Tanmay",
    "Umesh",
    "Vishal",
    "Abhishek",
    "Farhan",
    "Imran",
    "Junaid",
    "Khalid",
    "Irfan",
    "Nadeem",
    "Rashid",
    "Salman",
    "Tariq",
    "Wasim",
    "Zaheer",
    "Aamir",
    "Danish",
    "Faisal",
    "Hamid",
    "Javed",
    "Karim",
    "Mansoor",
    "Nasir",
    "Owais",
    "Qasim",
    "Raza",
    "Shahid",
    "Usman",
    "Baldev",
    "Charan",
    "Darshan",
    "Gurpreet",
    "Harjot",
    "Jaspreet",
    "Manpreet",
    "Paramjit",
    "Ranjit",
    "Simran",
    "Tejinder",
    "Amarjit",
)


def _stable_index(seed: int, index: int, gender: str, pool_size: int) -> int:
    digest = hashlib.md5(f"{seed}|{index}|{gender}".encode()).hexdigest()
    return int(digest, 16) % pool_size


def generate_persona_name(*, gender: str, index: int, seed: int) -> str:
    """Deterministically generate an Indian first name.

    Args:
        gender: ``"female"`` or ``"male"``.
        index: Persona index in generation order.
        seed: Master population seed.

    Returns:
        Deterministic name from the corresponding gender pool.
    """

    pool = FEMALE_NAMES if gender == "female" else MALE_NAMES
    chosen = _stable_index(seed=seed, index=index, gender=gender, pool_size=len(pool))
    return pool[chosen]


def generate_persona_id(
    *,
    name: str,
    city_name: str,
    gender: str,
    parent_age: int,
    index: int,
) -> str:
    """Generate a human-readable persona ID.

    Format: ``Name-City-Mom/Dad-Age``.

    Args:
        name: First name.
        city_name: City name from demographics.
        gender: ``"female"`` or ``"male"``.
        parent_age: Parent age.
        index: Persona index (kept for API compatibility and deterministic
            generation; uniqueness is resolved later if needed).

    Returns:
        Human-readable ID.
    """

    role = "Mom" if gender == "female" else "Dad"
    if " " in city_name:
        city = "".join(part.title() for part in city_name.split())
    else:
        city = city_name.title()
    _ = index
    return f"{name}-{city}-{role}-{int(parent_age)}"
