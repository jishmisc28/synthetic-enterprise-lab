"""Branches, products, names. Deterministic extras from an index."""

from __future__ import annotations

PRODUCTS = [
    {"product_code": "PL", "name": "Personal Loan", "family": "UNSECURED",
     "annual_rate": "0.1800", "min_p": 50000, "max_p": 1500000, "tenors": (12, 24, 36, 48)},
    {"product_code": "BNPL", "name": "Aarohan Pay", "family": "UNSECURED",
     "annual_rate": "0.2400", "min_p": 1000, "max_p": 25000, "tenors": (1, 3, 6)},
    {"product_code": "TW", "name": "Two Wheeler", "family": "VEHICLE",
     "annual_rate": "0.1550", "min_p": 40000, "max_p": 150000, "tenors": (12, 24, 36)},
    {"product_code": "UV", "name": "Used Vehicle", "family": "VEHICLE",
     "annual_rate": "0.1650", "min_p": 100000, "max_p": 800000, "tenors": (24, 36, 48)},
    {"product_code": "EDU", "name": "Education Loan", "family": "EDU",
     "annual_rate": "0.1150", "min_p": 200000, "max_p": 2500000, "tenors": (60, 84, 120)},
    {"product_code": "GOLD", "name": "Gold Loan", "family": "GOLD",
     "annual_rate": "0.1200", "min_p": 10000, "max_p": 2000000, "tenors": (3, 6, 12)},
]

# 32 branches: code, city, state, region, gold_counter, digital
_CITIES = [
    ("PNQ-KTH", "Pune Kothrud", "MH", "WEST", True),
    ("PNQ-HIN", "Pune Hinjawadi", "MH", "WEST", False),
    ("MUM-AND", "Mumbai Andheri", "MH", "WEST", True),
    ("MUM-THN", "Thane", "MH", "WEST", False),
    ("NGP-CEN", "Nagpur", "MH", "WEST", True),
    ("AHM-SG", "Ahmedabad SG", "GJ", "WEST", True),
    ("SUR-RNG", "Surat Ring", "GJ", "WEST", False),
    ("JAI-MI", "Jaipur MI", "RJ", "NORTH", True),
    ("DEL-SKT", "Delhi Saket", "DL", "NORTH", True),
    ("DEL-RHP", "Delhi Rohini", "DL", "NORTH", False),
    ("LKO-GOM", "Lucknow Gomti", "UP", "NORTH", False),
    ("BLR-JPN", "Bengaluru Jayanagar", "KA", "SOUTH", True),
    ("BLR-WFD", "Bengaluru Whitefield", "KA", "SOUTH", False),
    ("MYS-CEN", "Mysuru", "KA", "SOUTH", True),
    ("CHN-TNG", "Chennai T Nagar", "TN", "SOUTH", True),
    ("CHN-AMB", "Chennai Ambattur", "TN", "SOUTH", False),
    ("CBE-RS", "Coimbatore RS", "TN", "SOUTH", False),
    ("HYD-BAN", "Hyderabad Banjara", "TG", "SOUTH", True),
    ("HYD-KUK", "Hyderabad Kukatpally", "TG", "SOUTH", False),
    ("KOH-MG", "Kochi MG", "KL", "SOUTH", True),
    ("TVM-PTT", "Thiruvananthapuram", "KL", "SOUTH", False),
    ("KOL-SLK", "Kolkata Salt Lake", "WB", "EAST", True),
    ("KOL-HWR", "Howrah", "WB", "EAST", False),
    ("PAT-BOR", "Patna Boring", "BR", "EAST", False),
    ("BBI-SY", "Bhubaneswar", "OD", "EAST", False),
    ("IND-VJ", "Indore Vijay", "MP", "WEST", True),
    ("BPL-MP", "Bhopal", "MP", "WEST", False),
    ("CHD-SEC", "Chandigarh 17", "CH", "NORTH", False),
    ("LUD-FZH", "Ludhiana Feroze", "PB", "NORTH", False),
    ("VAD-ALK", "Vadodara Alkapuri", "GJ", "WEST", False),
    ("NSK-CG", "Nashik CG", "MH", "WEST", False),
    ("DIGITAL", "Digital / App", "IN", "DIGITAL", False),
]


def branches() -> list[dict]:
    out = []
    for i, (code, name, st, region, gold) in enumerate(_CITIES, start=1):
        out.append({
            "branch_id": i, "branch_code": code, "branch_name": name,
            "state": st, "region": region, "gold_counter": gold,
            "is_digital": code == "DIGITAL",
            "bm_email": f"bm.{code.lower()}@aarohan.example",
        })
    return out


FIRST = ("Aarav", "Vihaan", "Aditya", "Arjun", "Kabir", "Ishaan", "Reyansh",
         "Ananya", "Diya", "Myra", "Saanvi", "Aadhya", "Pari", "Ira")
LAST = ("Sharma", "Patel", "Reddy", "Nair", "Iyer", "Kulkarni", "Gupta",
        "Singh", "Das", "Joshi", "Mehta", "Pillai", "Banerjee", "Khan")


def person(i: int) -> tuple[str, str, str]:
    name = f"{FIRST[i % len(FIRST)]} {LAST[(i // len(FIRST)) % len(LAST)]}"
    pan = f"AHWPK{(i % 9000) + 1000:04d}{chr(65 + (i % 26))}"
    mobile = f"98{(20000000 + i) % 100000000:08d}"
    return name, pan, mobile


def dealers() -> list[dict]:
    return [
        {"dealer_code": "DL-HYD-01", "name": "Banjara Motors", "city": "Hyderabad", "region": "SOUTH"},
        {"dealer_code": "DL-PNQ-01", "name": "Deccan Wheels", "city": "Pune", "region": "WEST"},
        {"dealer_code": "DL-MUM-01", "name": "Western Auto", "city": "Mumbai", "region": "WEST"},
        {"dealer_code": "DL-BLR-01", "name": "Garden City Motors", "city": "Bengaluru", "region": "SOUTH"},
        {"dealer_code": "DL-DEL-01", "name": "NCR Wheels", "city": "Delhi", "region": "NORTH"},
        {"dealer_code": "DL-KOL-01", "name": "Howrah Ride", "city": "Kolkata", "region": "EAST"},
    ]


def agents() -> list[dict]:
    return [
        {"agent_code": "A-WEST-07", "name": "Suresh Kolekar", "region": "WEST",
         "agency_code": "HOUSE", "mgr_email": "collections.mgr.west@aarohan.example",
         "effective_from": "2026-01-01", "effective_to": None, "home_branch": "MUM-AND"},
        {"agent_code": "A-WEST-12", "name": "Meena Shah", "region": "WEST",
         "agency_code": "AAROHAN_COLLECT", "mgr_email": "collections.mgr.west@aarohan.example",
         "effective_from": "2024-09-01", "effective_to": None, "home_branch": "AHM-SG"},
        {"agent_code": "A-DIG-01", "name": "Digital Desk", "region": "DIGITAL",
         "agency_code": "HOUSE", "mgr_email": "collections.mgr.digital@aarohan.example",
         "effective_from": "2024-09-01", "effective_to": None, "home_branch": "DIGITAL"},
        {"agent_code": "A-SOUTH-03", "name": "Lakshmi Rao", "region": "SOUTH",
         "agency_code": "DHANSETU", "mgr_email": "collections.mgr.south@aarohan.example",
         "effective_from": "2024-09-01", "effective_to": None, "home_branch": "BLR-JPN"},
        {"agent_code": "A-NORTH-02", "name": "Aman Verma", "region": "NORTH",
         "agency_code": "HOUSE", "mgr_email": "collections.mgr.north@aarohan.example",
         "effective_from": "2024-09-01", "effective_to": None, "home_branch": "DEL-SKT"},
        {"agent_code": "A-EAST-04", "name": "Rina Das", "region": "EAST",
         "agency_code": "DHANSETU", "mgr_email": "collections.mgr.east@aarohan.example",
         "effective_from": "2024-09-01", "effective_to": None, "home_branch": "KOL-SLK"},
        # Stale transfer: A-WEST-07 previously coded to Pune
        {"agent_code": "A-WEST-07", "name": "Suresh Kolekar", "region": "WEST",
         "agency_code": "HOUSE", "mgr_email": "collections.mgr.west@aarohan.example",
         "effective_from": "2024-09-01", "effective_to": "2025-12-31", "home_branch": "PNQ-HIN"},
    ]
