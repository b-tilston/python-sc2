import sys, os
import sc2

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import numpy as np
from sc2.position import Point2, Point3
from sc2.data import *
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.player import Bot, Computer
from sc2.unit import Unit
from sc2.units import Units
from sc2.game_info import *
from sc2.game_data import *


class RoachCounterBot(sc2.BotAI):
    async def on_start(self):
        self.client.game_step = 2

    async def on_step(self, iteration):
        # If townhall no longer exists: attack move with all units to enemy start location
        if not self.townhalls:
            for unit in self.units.exclude_type({UnitTypeId.EGG, UnitTypeId.LARVA}):
                unit.attack(self.enemy_start_locations[0])
            return

        hatch: Unit = self.townhalls[0]
        if self.can_afford(AbilityId.RESEARCH_BURROW):
            hatch(AbilityId.RESEARCH_BURROW)

        # Pick a target location
        target: Point2 = self.enemy_structures.not_flying.random_or(self.enemy_start_locations[0]).position

        # Give all zerglings an attack command
        for zergling in self.units(UnitTypeId.ZERGLING):
            if (self.units(UnitTypeId.ZERGLING).amount + self.units(UnitTypeId.ROACH).amount) > 50:
                zergling.attack(target)  
            else:   
                position: Set[Point2] = self.main_base_ramp.points
                ramp: Point2 = position.pop() 
                zergling.patrol(ramp) 

        # Give all roaches an attack command
        for roach in self.units(UnitTypeId.ROACH):
            if (self.units(UnitTypeId.ZERGLING).amount + self.units(UnitTypeId.ROACH).amount) > 50:
                roach.attack(target)
            else:
                position: Set[Point2] = self.main_base_ramp.points
                ramp: Point2 = position.pop() 
                roach.patrol(ramp) 
        # ravager attack command
                
        # Inject hatchery if queen has more than 25 energy
        for queen in self.units(UnitTypeId.QUEEN):
            if queen.energy >= 25 and not hatch.has_buff(BuffId.QUEENSPAWNLARVATIMER):
                queen(AbilityId.EFFECT_INJECTLARVA, hatch)

        # Have roach units burrow if below 1/3 hp
        for roach in self.units(UnitTypeId.ROACH):
            if roach.health_percentage < 1 / 3:
                roach(AbilityId.BURROWDOWN_ROACH)
            
        # Have burrowed roach unborrow if above 9/10 hp
        for burroach in self.units(UnitTypeId.ROACHBURROWED):
            if burroach.health_percentage > 9 / 10:
                burroach(AbilityId.BURROWUP_ROACH)


        # Pull workers out of gas if we have almost enough gas mined, this will stop mining when we reached 100 gas mined
        # if self.vespene >= 88 or self.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) > 0:
        #     gas_drones: Units = self.workers.filter(lambda w: w.is_carrying_vespene and len(w.orders) < 2)
        #     drone: Unit
        #     for drone in gas_drones:
        #         minerals: Units = self.mineral_field.closer_than(10, hatch)
        #         if minerals:
        #             mineral: Unit = minerals.closest_to(drone)
        #             drone.gather(mineral, queue=True)

        # If we have 100 vespene, this will try to research zergling speed once the spawning pool is at 100% completion
        # if self.already_pending_upgrade(UpgradeId.ZERGLINGMOVEMENTSPEED) == 0 and self.can_afford(UpgradeId.ZERGLINGMOVEMENTSPEED):
        # #if self.already_pending_upgrade(UpgradeId.ZERGLINGATTACKSPEED) == 0 and self.can_afford(UpgradeId.ZERGLINGATTACKSPEED):
        #     spawning_pools_ready: Units = self.structures(UnitTypeId.SPAWNINGPOOL).ready
        #     if spawning_pools_ready:
        #         self.research(UpgradeId.ZERGLINGMOVEMENTSPEED)

        
        # If we have less than 2 supply left and no overlord is in the queue: train an overlord
        if self.supply_left < 2 and self.already_pending(UnitTypeId.OVERLORD) < 1:
            self.train(UnitTypeId.OVERLORD, 1)

        # While we have less than 88 vespene mined: send drones into extractor one frame at a time
        elif self.gas_buildings.ready:
            extractor: Unit = self.gas_buildings.first
            if extractor.surplus_harvesters < 0:
                self.workers.random.gather(extractor)

        # If we have lost of minerals, make a macro hatchery
        if self.minerals > 500 and self.structures(UnitTypeId.HATCHERY).amount < 2:
            for d in range(1, 50):
                pos: Point2 = hatch.position.towards(self.game_info.map_center, d)
                if await self.can_place_single(UnitTypeId.HATCHERY, pos):
                    drone: Unit = self.workers.closest_to(pos)
                    drone.build(UnitTypeId.HATCHERY, pos)
        

        # While we have less than 16 drones, make more drones
        if self.can_afford(UnitTypeId.DRONE) and self.supply_workers < 19:
            self.train(UnitTypeId.DRONE)

        # If our spawningpool is completed and we have more than 30 zerglings ready or pending and a roach warren ready train roaches, otherwise train zerglings
        for hatchery in self.structures(UnitTypeId.HATCHERY) or lair in self.structures(UnitTypeId.LAIR):
            if ((self.larva.amount + self.already_pending(UnitTypeId.ZERGLING) + self.units(UnitTypeId.ZERGLING).amount) >= 30) and self.structures(UnitTypeId.ROACHWARREN).amount == 1:
                if self.can_afford(UnitTypeId.ROACH):
                    self.train(UnitTypeId.ROACH)
            elif self.structures(UnitTypeId.SPAWNINGPOOL).ready and self.larva and self.can_afford(UnitTypeId.ZERGLING):
                self.train(UnitTypeId.ZERGLING)
                
        
        # If the roach warren is complete, start training roaches
        # if self.structures(UnitTypeId.ROACHWARREN).ready and self.can_afford(UnitTypeId.ROACH):
        #     self.train(UnitTypeId.ROACH, self.larva.amount)

        # If we have no extractor, build extractor
        if (self.gas_buildings.amount + self.already_pending(UnitTypeId.EXTRACTOR) < 1 and self.can_afford(UnitTypeId.EXTRACTOR) and self.workers):
            drone: Unit = self.workers.random
            target: Unit = self.vespene_geyser.closest_to(drone)
            drone.build_gas(target)


        # If we have no spawning pool, try to build spawning pool
        elif self.structures(UnitTypeId.SPAWNINGPOOL).amount + self.already_pending(UnitTypeId.SPAWNINGPOOL) == 0:
            if self.can_afford(UnitTypeId.SPAWNINGPOOL):
                for d in range(4, 15):
                    pos: Point2 = hatch.position.towards(self.game_info.map_center, d)
                    if await self.can_place_single(UnitTypeId.SPAWNINGPOOL, pos):
                        drone: Unit = self.workers.closest_to(pos)
                        drone.build(UnitTypeId.SPAWNINGPOOL, pos)
        
        # If we have more than 1 hatchery, begin building a roach warren: 
        elif self.structures(UnitTypeId.SPAWNINGPOOL).amount >= 1 and (self.structures(UnitTypeId.ROACHWARREN).amount + self.already_pending(UnitTypeId.ROACHWARREN) == 0) and self.units(UnitTypeId.ZERGLING).amount > 15:
            for c in range(4,15):
                pos: Point2 = (self._game_info.player_start_location)
                pool: Unit = self.structures(UnitTypeId.SPAWNINGPOOL).first
                placement = await self.find_placement(UnitTypeId.ROACHWARREN, near=pos, placement_step=1)
                if await (self.can_place(UnitTypeId.ROACHWARREN, placement)):
                    drone: Unit = self.workers.closest_to(pos)
                    drone.build(UnitTypeId.ROACHWARREN, placement)
        
      

        # If we have no Evo Chamber, try and build one
        elif self.structures(UnitTypeId.EVOLUTIONCHAMBER).amount + self.already_pending(UnitTypeId.EVOLUTIONCHAMBER) == 0 and self.units(UnitTypeId.ZERGLING).amount > 15:
            if self.can_afford(UnitTypeId.EVOLUTIONCHAMBER):
                for e in range(4, 15):
                    pos: Point2 = hatch.position.towards(self.game_info.map_center, e)
                    if await self.can_place_single(UnitTypeId.EVOLUTIONCHAMBER, pos):
                        drone: Unit = self.workers.closest_to(pos)
                        drone.build(UnitTypeId.EVOLUTIONCHAMBER, pos)

        if self.structures(UnitTypeId.EVOLUTIONCHAMBER).amount > 0:
            evo: Unit = self.structures(UnitTypeId.EVOLUTIONCHAMBER).first
            L1upgrades = [UpgradeId.ZERGGROUNDARMORSLEVEL1, UpgradeId.ZERGMELEEWEAPONSLEVEL1, UpgradeId.ZERGMISSILEWEAPONSLEVEL1]
            L2upgrades = [UpgradeId.ZERGGROUNDARMORSLEVEL2, UpgradeId.ZERGMELEEWEAPONSLEVEL2, UpgradeId.ZERGMISSILEWEAPONSLEVEL2] 
            L3upgrades = [UpgradeId.ZERGGROUNDARMORSLEVEL3, UpgradeId.ZERGMELEEWEAPONSLEVEL3, UpgradeId.ZERGMISSILEWEAPONSLEVEL3]
            for L1upgrade in L1upgrades:
                evo.research(L1upgrade)
            if self.structures(UnitTypeId.LAIR).amount >= 0:
                for L2upgrade in L2upgrades:
                    evo.research(L2upgrade)
            if self.structures(UnitTypeId.HIVE).amount >= 0:
                for L3upgrade in L3upgrades:
                    evo.research(L3upgrade)

        # If we have no queen, try to build a queen if we have a spawning pool compelted
        #elif (self.units(UnitTypeId.QUEEN).amount + self.already_pending(UnitTypeId.QUEEN) < self.townhalls.amount and self.structures(UnitTypeId.SPAWNINGPOOL).ready):
        if self.structures(UnitTypeId.SPAWNINGPOOL).ready and self.can_afford(UnitTypeId.QUEEN) and (self.units(UnitTypeId.QUEEN).amount + self.already_pending(UnitTypeId.QUEEN) < 2):
            self.train(UnitTypeId.QUEEN)
        
        # If we can afford to and have more than 1 hatchery, upgrade our primary hatchery to a lair
        elif self.units(UnitTypeId.HATCHERY).amount > 1 and self.can_afford(UnitTypeId.LAIR):
            hatch: Unit = self.structures(UnitTypeId.HATCHERY)
            if self.already_pending(UnitTypeId.LAIR) < 1: 
                hatch(AbilityId.UPGRADETOLAIR_LAIR)
        
        # elif self.units(UnitTypeId.LAIR).amount == 1:
        #     lair: Unit = self.structures(UnitTypeId.LAIR).first
        #     if self.can_afford(UnitTypeId.HIVE) and self.already_pending(UnitTypeId.HIVE) == 0:
        #         lair(AbilityId.UPGRADETOHIVE_HIVE)

    def draw_creep_pixelmap(self):
        for (y, x), value in np.ndenumerate(self.state.creep.data_numpy):
            p = Point2((x, y))
            h2 = self.get_terrain_z_height(p)
            pos = Point3((p.x, p.y, h2))
            # Red if there is no creep
            color = Point3((255, 0, 0))
            if value == 1:
                # Green if there is creep
                color = Point3((0, 255, 0))
            self._client.debug_box2_out(pos, half_vertex_length=0.25, color=color)

    async def on_end(self, game_result: Result):
        print(f"{self.time_formatted} On end was called")


def main():
    sc2.run_game(
        sc2.maps.get("AcropolisLE"),
        [Bot(Race.Zerg, RoachCounterBot()), Computer(Race.Terran, Difficulty.Medium)],
        realtime=False,
        save_replay_as="ZvT.SC2Replay",
    )


if __name__ == "__main__":
    main()
