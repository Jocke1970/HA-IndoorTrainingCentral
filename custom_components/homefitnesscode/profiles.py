"""Bluetooth protocol profiles: standard FTMS and HomeFitnessCode FTMS."""
from .protocol import PARSERS

class FTMSProfile:
    name = "ftms"

    def parse(self, machine_type: str, payload: bytes) -> dict:
        return PARSERS[machine_type](payload)

class HomeFitnessCodeProfile(FTMSProfile):
    name = "homefitnesscode"

def make_profile(name: str) -> FTMSProfile:
    return HomeFitnessCodeProfile() if name == "homefitnesscode" else FTMSProfile()
