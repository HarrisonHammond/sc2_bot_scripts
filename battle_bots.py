from prime_bot import PrimeBot
from cool_guy_bot import CoolGuyBot
from sc2 import maps
from sc2.main import run_game
from sc2.player import (
    Bot,
    Computer,
    Human,
)
from sc2.data import Race

if __name__ == "__main__":
    run_game(
        maps.get("RomanticideAIE"),
        [
            Bot(Race.Zerg, CoolGuyBot()),
            Bot(Race.Terran, PrimeBot()),
        ],
        realtime=False,
    )
