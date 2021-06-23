import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import sc2
from sc2 import Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.buff_id import BuffId
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.player import Bot, Computer


class ZealotRushBot(sc2.BotAI):
    def __init__(self):
        # Initialize inherited class
        sc2.BotAI.__init__(self)
        self.proxy_built = False

    async def on_step(self, iteration):
        await self.distribute_workers()

        if not self.townhalls.ready:
            # Attack with all workers if we don't have any nexuses left, attack-move on enemy spawn (doesn't work on 4 player map) so that probes auto attack on the way
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])
            return
        else:
            nexus = self.townhalls.ready.random

        # Build pylon when on low supply
        if self.supply_left < 2 and self.already_pending(UnitTypeId.PYLON) == 0:
            # Always check if you can afford something before you build it
            if self.can_afford(UnitTypeId.PYLON):
                await self.build(UnitTypeId.PYLON, near=nexus)
                
               
            return

        # Build pylons if we have less than 5 and none pending
        elif self.structures(UnitTypeId.PYLON).amount < 3 and self.already_pending(UnitTypeId.PYLON) == 0:
            if self.can_afford(UnitTypeId.PYLON):
                await self.build(UnitTypeId.PYLON, near=nexus.position.towards(self.game_info.map_center, 2))

        # Train Zealots
        for gateway in self.structures(UnitTypeId.GATEWAY).ready.idle:
            if (self.can_afford(UnitTypeId.ZEALOT) and self.already_pending(UnitTypeId.ZEALOT) == 0):
                gateway.train(UnitTypeId.ZEALOT)
                    
        # Train more probes if probe amount < 22 and we have an idle nexus
        if self.workers.amount < self.townhalls.amount * 22 and nexus.is_idle: #22
            if self.can_afford(UnitTypeId.PROBE):
                nexus.train(UnitTypeId.PROBE)

        # Build Gateways if gateway count is below 3 and we have pylons ready and can afford to build a gateway
        if self.structures(UnitTypeId.PYLON).ready and self.can_afford(UnitTypeId.GATEWAY):
            global pylon
            pylon = self.structures(UnitTypeId.PYLON).random
            if self.structures(UnitTypeId.GATEWAY).amount < 4:
                await self.build(UnitTypeId.GATEWAY, near=pylon.position.towards(self.game_info.map_center, 3)) #near=pylon.position)
        
        # Build Forge if we have a gateway ready and more than 2 gateways
        if self.structures(UnitTypeId.GATEWAY).ready and self.structures(UnitTypeId.GATEWAY).amount > 0:
                # If we have no Forge, build one
            pylon = pylon_ready = self.structures(UnitTypeId.PYLON).ready
            if not self.structures(UnitTypeId.FORGE):
                if (self.can_afford(UnitTypeId.FORGE) and self.already_pending(UnitTypeId.FORGE) == 0):
                    await self.build(UnitTypeId.FORGE, near=pylon.furthest_to(nexus))

        # Build Cybernetics Core if we have a gateway ready and can afford it
        if self.can_afford(UnitTypeId.CYBERNETICSCORE) and self.structures(UnitTypeId.CYBERNETICSCORE).amount == 0:
           await self.build(UnitTypeId.CYBERNETICSCORE, near=nexus)

        # Build a Twilight Council if we can afford it, then research zealot "charge ability" when construction complete
        if self.structures(UnitTypeId.CYBERNETICSCORE).ready: 
            if self.can_afford(UnitTypeId.TWILIGHTCOUNCIL) and self.structures(UnitTypeId.TWILIGHTCOUNCIL).amount == 0:
                pylon = self.structures(UnitTypeId.PYLON).random
                await self.build(UnitTypeId.TWILIGHTCOUNCIL, near=pylon.position.towards(self.game_info.map_center, 6))
                if self.structures(UnitTypeId.TWILIGHTCOUNCIL).amount > 0:
                    self.research(UpgradeId.CHARGE)

        # Build gas
        for nexus in self.townhalls.ready:
            vgs = self.vespene_geyser.closer_than(15, nexus)
            for vg in vgs:
                if not self.can_afford(UnitTypeId.ASSIMILATOR):
                    break
                worker = self.select_build_worker(vg.position)
                if worker is None:
                    break
                if not self.gas_buildings or not self.gas_buildings.closer_than(1, vg):
                    worker.build(UnitTypeId.ASSIMILATOR, vg)
                    worker.stop(queue=True)
                    
        # make zealots move between nexus and somewhere else to try and force fights with invading enemy forces to the base
        #if self.units(UnitTypeId.ZEALOT).amount >= 1 and self.units(UnitTypeId.ZEALOT).amount < 8:
        for zealot in self.units(UnitTypeId.ZEALOT).ready.idle:
            zealot.patrol(self.start_location.towards(self.game_info.map_center, 6))
            zealot.patrol(nexus)
            zealot.patrol(vg)
            
        # Make zealots attack either closest enemy unit or enemy spawn location
        #if self.units(UnitTypeId.ZEALOT).amount > 7:
            #for zealot in self.units(UnitTypeId.ZEALOT).ready: #.idle
                #targets = (self.enemy_units | self.enemy_structures).filter(lambda unit: unit.can_be_attacked)
                #if targ:
                    #target = targets.closest_to(zealot)
                    #zealot.attack(target)
                #else:
                    #zealot.attack(self.enemy_start_locations[0])

        # Distinguish between enemy units and buildings and prioritise enemy units
        enemies: Units = self.enemy_units | self.enemy_structures
        enemies_can_attack: Units = enemies.filter(lambda unit: unit.can_attack_ground)
        if self.units(UnitTypeId.ZEALOT).amount > 8:
            for zealot in self.units(UnitTypeId.ZEALOT):
                enemyThreatsClose: Units = enemies_can_attack.filter(
                    lambda unit: not unit.is_structure
                    and not unit.is_flying
                    and unit.type_id not in {UnitTypeId.LARVA, UnitTypeId.EGG})
                if zealot.weapon_cooldown == 0 and enemyThreatsClose: 
                    closestEnemy: Unit = enemyThreatsClose[0]
                    zealot.attack(closestEnemy)
                else:
                    zealot.attack(self.enemy_start_locations[0])


        # Make the Forge start upgrading, alternating between w1 and a1, then w2 and a2 etc until fully upgraded when Twilight Council is built
        if self.structures(UnitTypeId.FORGE).ready:
            forge = self.structures(UnitTypeId.FORGE)
            L1upgrades = [UpgradeId.PROTOSSGROUNDWEAPONSLEVEL1, UpgradeId.PROTOSSSHIELDSLEVEL1, UpgradeId.PROTOSSGROUNDARMORSLEVEL1]
            L2L3upgrades = [UpgradeId.PROTOSSGROUNDWEAPONSLEVEL2, UpgradeId.PROTOSSGROUNDWEAPONSLEVEL3, UpgradeId.PROTOSSSHIELDSLEVEL2, 
                            UpgradeId.PROTOSSSHIELDSLEVEL3, UpgradeId.PROTOSSGROUNDARMORSLEVEL2, UpgradeId.PROTOSSGROUNDARMORSLEVEL3]
            for L1upgrade in (L1upgrades):
                if self.already_pending_upgrade(L1upgrade) == 0 and self.can_afford(L1upgrade):
                    self.research(L1upgrade)
            for L2L3upgrade in L2L3upgrades:
                if self.structures(UnitTypeId.TWILIGHTCOUNCIL).amount > 0:
                    if self.already_pending_upgrade(L2L3upgrade) == 0 and self.can_afford(L2L3upgrade):
                        self.research(L2L3upgrade)
                    else:
                        continue


        # Chrono nexus if gateway and forge are not ready, else if only forge is not ready, Chrono gateway else chrono Forge
        if not self.structures(UnitTypeId.FORGE).ready and self.structures(UnitTypeId.GATEWAY).ready:
            if not nexus.has_buff(BuffId.CHRONOBOOSTENERGYCOST) and not nexus.is_idle:
                if nexus.energy >= 50:
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, nexus)
        elif self.structures(UnitTypeId.FORGE).ready == False and self.structures(UnitTypeId.GATEWAY).ready == True:
            gateway = self.structures(UnitTypeId.GATEWAY).ready.first
            if not gateway.has_buff(BuffId.CHRONOBOOSTENERGYCOST) and not gateway.is_idle:
                if nexus.energy >= 50:
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, gateway)    
        elif self.structures(UnitTypeId.FORGE).ready: 
            forge = self.structures(UnitTypeId.FORGE).ready.first
            if not forge.has_buff(BuffId.CHRONOBOOSTENERGYCOST) and not forge.is_idle:
                if nexus.energy >= 50:
                    nexus(AbilityId.EFFECT_CHRONOBOOSTENERGYCOST, forge)


def main():
    sc2.run_game(
        sc2.maps.get("(2)CatalystLE"),
        [Bot(Race.Protoss, ZealotRushBot()), Computer(Race.Protoss, Difficulty.Easy)],
        realtime=False,
    )


if __name__ == "__main__":
    main()
