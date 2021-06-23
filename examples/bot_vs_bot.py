import sc2
from sc2 import Race
from sc2.player import Bot

from zerg.zerg_rush import ZergRushBot
from protoss.zealot_rush import ZealotRushBot
from zerg.hydralisk_push import Hydralisk
from terran.proxy_rax import ProxyRaxBot
from terran.hellion import HellionBot
from protoss.threebase_voidray import ThreebaseVoidrayBot
from terran.mass_reaper import MassReaperBot
from zerg.roach_counter import RoachCounterBot


def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"),
        [Bot(Race.Protoss, ZealotRushBot()), Bot(Race.Zerg, ZergRushBot())],
        realtime=False,
        save_replay_as="Example.SC2Replay",
    )


if __name__ == "__main__":
    main()
