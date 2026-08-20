#!/usr/bin/env python3
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from src.resume_parser import load_profile

def main():
    p = load_profile()
    print("Skills found in resume:")
    print(p.skills)
    print(f"\nProfile: {p.name} <{p.email}>")
    print(f"Raw preview: {p.raw_text[:400]}...")

if __name__ == "__main__":
    main()
