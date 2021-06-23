""" 
Bot that stays on 1 base initially, bunkering marines until it can churn out hellions and upgrades
This bot is one of the first examples that are micro intensive
Bot has a chance to win against elite (=Difficulty.VeryHard) zerg AI

Bot made by Ben
"""

import sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

import random

import sc2
from sc2 import Race, Difficulty
from sc2.constants import *
from sc2.position import *
from sc2.unit import Unit
from sc2.player import Bot, Computer
from sc2.player import Human
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.units import Units
from sc2.game_info import *



class HellionBot(sc2.BotAI):
    
    def __init__(self):
        # Select distance calculation method 0, which is the pure python distance calculation without caching or indexing, using math.hypot(), for more info see distances.py _distances_override_functions() function
        self.distance_calculation_method = 0

    async def on_step(self, iteration):
        await self.distribute_workers()
        self.draw_ramp_points()


        CCs: Units = self.townhalls(UnitTypeId.COMMANDCENTER) 
        cc: Unit = CCs.first
        # Train more SCVs
        if (self.can_afford(UnitTypeId.SCV) and self.units(UnitTypeId.SCV).amount < 20 and cc.is_idle):
            cc.train(UnitTypeId.SCV)


        #If constrained by Supply, build supply depots
        if (
            self.supply_left < 5
            and self.townhalls
            and self.supply_used >= 14
            and self.can_afford(UnitTypeId.SUPPLYDEPOT)
            and self.already_pending(UnitTypeId.SUPPLYDEPOT) < 1
        ):
            workers: Units = self.workers.gathering
            # If workers were found
            if workers:
                worker: Unit = workers.furthest_to(workers.center)
                location: Point2 = await self.find_placement(UnitTypeId.SUPPLYDEPOT, worker.position, placement_step=3)
                # If a placement location was found
                if location:
                    # Order worker to build exactly on that location
                    worker.build(UnitTypeId.SUPPLYDEPOT, location)

        # Lower all depots when finished
        for depot in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        # Build Bunkers in base in good positions
        #cc = self.townhalls[0]
        workers: Units = self.workers.gathering
        bunker_placement_positions: Set[Point2] = self.main_base_ramp.upper
        bunkers: Units = self.structures.of_type(UnitTypeId.BUNKER) 
        if bunkers:
            bunker_placement_positions: Set[Point2] = {b for b in bunker_placement_positions if bunkers.closest_distance_to(b) > 3}
        
        if self.can_afford(UnitTypeId.BUNKER) and self.units(UnitTypeId.SCV).ready and self.structures(UnitTypeId.BUNKER).amount < 1:
            if len(bunker_placement_positions) == 0:
                return
            # If workers were found
            if workers:
                worker: Unit = workers.furthest_to(workers.center)
                bunker_location: Point2 = bunker_placement_positions.pop() #self.find_placement(UnitTypeId.BUNKER, near=pos, placement_step=3) #(UnitTypeId.BUNKER, placement_step=2)
                location: Point2 = await self.find_placement(UnitTypeId.BUNKER, near=bunker_location, placement_step=2)
                if location:
                    (worker.build(UnitTypeId.BUNKER, location))         
                    

        # Build Refinery
        for cc in self.townhalls.ready:
            vgs = self.vespene_geyser.closer_than(15, cc)
            for vg in vgs:
                if not self.can_afford(UnitTypeId.REFINERY):
                    break
                worker = self.select_build_worker(vg.position)
                if worker is None:
                    break
                if not self.gas_buildings or not self.gas_buildings.closer_than(1, vg):
                    worker.build(UnitTypeId.REFINERY, vg)
                    worker.stop(queue=True)

        # Train Marines until more than 7 units
        for rax in self.structures(UnitTypeId.BARRACKS).ready.idle: 
            if self.can_afford(UnitTypeId.MARINE) and self.units(UnitTypeId.MARINE).amount < 8:
                rax.train(UnitTypeId.MARINE)

        # Move Marines into Bunkers 
        for bunker in self.structures(UnitTypeId.BUNKER):
            marines = self.units(UnitTypeId.MARINE).ready 
            for marine in marines:
                bunker(AbilityId.LOAD_BUNKER, marine) #marine.smart(bunker)

        # Non-Garrisoned Marines Attack Logic:
        marines: Units = self.units(UnitTypeId.MARINE).idle
        if marines.amount > 7:
            target: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
            for marine in marines:
                marine.attack(target)

        # Transform from Hellion to Hellbat and vice versa
        if self.structures.of_type(UnitTypeId.FACTORY).ready and self.structures.of_type(UnitTypeId.ARMORY).ready:
            for hellion in self.units(UnitTypeId.HELLION):
                allEnemyGroundUnits: Units = self.enemy_units.not_flying
                enemies: Units = self.enemy_units | self.enemy_structures
                if enemies.amount > 5:
                    hellion(AbilityId.MORPH_HELLBAT)
                    continue

            
            for hellbat in self.units(UnitTypeId.HELLIONTANK):
                allEnemyGroundUnits: Units = self.enemy_units.not_flying
                if hellbat and allEnemyGroundUnits.amount < 1:
                    hellbat(AbilityId.MORPH_HELLION)
                    continue
        
        # Hellbat Attack Logic
        hellbats: Units =  self.units(UnitTypeId.HELLIONTANK).idle
        target: Point2 = self.enemy_structures.random_or(self.enemy_start_locations[0]).position
        for hellbat in hellbats:
            hellbat.attack(target)

        # Build Barracks 
        if self.can_afford(UnitTypeId.BARRACKS) and self.units(UnitTypeId.SCV).ready and self.structures(UnitTypeId.BARRACKS).amount < 1:
            location: Point2 = await self.find_placement(UnitTypeId.BARRACKS, near=cc.position, placement_step=3)
            await self.build(UnitTypeId.BARRACKS, near=location)

        # Build Factory
        if self.can_afford(UnitTypeId.FACTORY) and self.units(UnitTypeId.SCV).ready and self.structures(UnitTypeId.FACTORY).amount < 1 and self.structures(UnitTypeId.FACTORYFLYING).amount < 1 and self.structures(UnitTypeId.FACTORYTECHLAB).amount < 1:
            rax: unit = self.structures(UnitTypeId.BARRACKS).first
            location: Point2 = await self.find_placement(UnitTypeId.FACTORY, near=rax.position.towards(self.game_info.map_center, 6))
            await self.build(UnitTypeId.FACTORY, near=location)
             
        # Build Armory
        if self.can_afford(UnitTypeId.ARMORY) and self.units(UnitTypeId.SCV).ready and self.structures(UnitTypeId.ARMORY).amount < 2:
            location: Point2 = await self.find_placement(UnitTypeId.ARMORY, near=cc.position, placement_step=5)
            await self.build(UnitTypeId.ARMORY, near=location)
        
        # Train Hellions
        if self.structures(UnitTypeId.FACTORYTECHLAB).ready.idle:
            if self.can_afford(UnitTypeId.HELLION) and self.units(UnitTypeId.HELLION).amount < 10:
                self.train(UnitTypeId.HELLION)
                if self.already_pending_upgrade(UpgradeId.SMARTSERVOS) or self.already_pending(AbilityId.RESEARCH_INFERNALPREIGNITER):
                   self.train(UnitTypeId.HELLION)
                

        # Research Vehicle upgrades in armory
        if self.structures(UnitTypeId.ARMORY).ready:          
            for armory in self.structures(UnitTypeId.ARMORY):
                upgrades = [AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL1, AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL2,
                            AbilityId.ARMORYRESEARCH_TERRANVEHICLEANDSHIPPLATINGLEVEL3, AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL1,
                            AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL2, AbilityId.ARMORYRESEARCH_TERRANVEHICLEWEAPONSLEVEL3]
                for upgrade in (upgrades):
                    armory(upgrade)
                    
        # Add tech lab to factory
        if self.structures(UnitTypeId.FACTORY).ready:
            factory: Unit = self.structures(UnitTypeId.FACTORY).first
            factory.build(UnitTypeId.FACTORYTECHLAB)
            if self.structures(UnitTypeId.FACTORYTECHLAB).ready:
                techlab = self.structures(UnitTypeId.FACTORYTECHLAB).first
                tlupgrades = [AbilityId.RESEARCH_INFERNALPREIGNITER, AbilityId.RESEARCH_SMARTSERVOS]
                for tlupgrade in tlupgrades:
                    techlab(tlupgrade)
        #     factory(AbilityId.BUILD_TECHLAB_FACTORY)#(AbilityId.LIFT_FACTORY)
            
            # if self.structures(UnitTypeId.FACTORYFLYING):
            #     factoryfly: Unit = self.structures(UnitTypeId.FACTORYFLYING).idle
            #     techlab_position: Point2 = await self.find_placement(factoryfly, near=cc.add_on_land_position)
            #     if techlab_position == 0:
            #         return
            #     if techlab_position:
            #         factoryfly.build(UnitTypeId.FACTORYTECHLAB)#, factoryfly, techlab_position)


        def factory_points_to_build_addon(factory_position: Point2) -> List[Point2]:
            """ Return all points that need to be checked when trying to build an addon. Returns 4 points. """
            addon_offset: Point2 = Point2((2.5, -0.5))
            addon_position: Point2 = factory_position + addon_offset
            addon_points = [
                (addon_position + Point2((x - 0.5, y - 0.5))).rounded for x in range(0, 2) for y in range(0, 2)
            ]
            return addon_points

        # # Build starport techlab or lift if no room to build techlab
        # factory: Unit
        # for factory in self.structures(UnitTypeId.FACTORY).ready.idle:
        #     if not factory.has_add_on and self.can_afford(UnitTypeId.FACTORYTECHLAB):
        #         addon_points = factory_points_to_build_addon(factory.position)
        #         if all(
        #             self.in_map_bounds(addon_point)
        #             and self.in_placement_grid(addon_point)
        #             and self.in_pathing_grid(addon_point)
        #             for addon_point in addon_points
        #         ):
        #             factory.build(UnitTypeId.FACTORYTECHLAB)

        # repair damaged bunkers
        for b in self.structures(UnitTypeId.BUNKER):
            SCVs: Units = self.units(UnitTypeId.SCV)
            SCV: Unit = SCVs.closest_to(b)
            if b.health_percentage < 1 / 2 and SCVs:
                SCV(AbilityId.EFFECT_REPAIR_SCV, b)

        # Research Smart Servos and Infernal Pre-Igniter

       
        

        # Hellion Kiting taken from reaper
        enemies: Units = self.enemy_units | self.enemy_structures
        enemies_can_attack: Units = enemies.filter(lambda unit: unit.can_attack_ground)
        for h in self.units(UnitTypeId.HELLION):
            # Move to range 15 of closest unit if Hellion is below 20 hp and not regenerating
            enemyThreatsClose: Units = enemies_can_attack.filter(lambda unit: unit.distance_to(h) < 15)  
            
            # Threats that can attack the reaper
            if h.health_percentage < 1 / 100 and enemyThreatsClose:
                retreatPoints: Set[Point2] = self.neighbors8(h.position, distance=4) | self.neighbors8(h.position, distance=5)
                # Filter points that are pathable
                retreatPoints: Set[Point2] = {x for x in retreatPoints if self.in_pathing_grid(x)}
                if retreatPoints:
                    closestEnemy: Unit = enemyThreatsClose.closest_to(h)
                    retreatPoint: Unit = closestEnemy.position.furthest(retreatPoints)
                    h.move(retreatPoint)
                    continue  # Continue for loop, dont execute any of the following

            # Hellion is ready to attack, shoot nearest ground unit
            enemyGroundUnits: Units = enemies.filter(lambda unit: unit.distance_to(h) < 5 and not unit.is_flying)  
                # Hardcoded attackrange of 5
            if h.weapon_cooldown == 0 and enemyGroundUnits:
                enemyGroundUnits: Units = enemyGroundUnits.sorted(lambda x: x.distance_to(h))
                closestEnemy: Unit = enemyGroundUnits[0]
                h.attack(closestEnemy)
                continue  # Continue for loop, dont execute any of the following

            # Move to max unit range if enemy is closer than 4
            enemyThreatsVeryClose: Units = enemies.filter(lambda unit: unit.can_attack_ground and unit.distance_to(h) < 4.5)  # Hardcoded attackrange minus 0.5
            # Threats that can attack the Hellion
            if h.weapon_cooldown != 0 and enemyThreatsVeryClose:
                retreatPoints: Set[Point2] = self.neighbors8(h.position, distance=2) | self.neighbors8(h.position, distance=3)
                # Filter points that are pathable by a Hellion
                retreatPoints: Set[Point2] = {x for x in retreatPoints if self.in_pathing_grid(x)}
                if retreatPoints:
                    closestEnemy: Unit = enemyThreatsVeryClose.closest_to(h)
                    retreatPoint: Point2 = max(retreatPoints, key=lambda x: x.distance_to(closestEnemy) - x.distance_to(h))
                    h.move(retreatPoint)
                    continue  # Continue for loop, don't execute any of the following

            # Move to nearest enemy ground unit/building because no enemy unit is closer than 5
            allEnemyGroundUnits: Units = self.enemy_units.not_flying
            if allEnemyGroundUnits:
                closestEnemy: Unit = allEnemyGroundUnits.closest_to(h)
                h.move(closestEnemy)
                continue  # Continue for loop, don't execute any of the following

            # Move to random enemy start location if no enemy buildings have been seen
            h.move(random.choice(self.enemy_start_locations))
                
    

        # Stolen and modified from position.py
    def neighbors4(self, position, distance=1) -> Set[Point2]:
        p = position
        d = distance
        return {Point2((p.x - d, p.y)), Point2((p.x + d, p.y)), Point2((p.x, p.y - d)), Point2((p.x, p.y + d))}

    # Stolen and modified from position.py
    def neighbors8(self, position, distance=1) -> Set[Point2]:
        p = position
        d = distance
        return self.neighbors4(position, distance) | {
            Point2((p.x - d, p.y - d)),
            Point2((p.x - d, p.y + d)),
            Point2((p.x + d, p.y - d)),
            Point2((p.x + d, p.y + d)),
        }
    def draw_ramp_points(self):
        for ramp in self.game_info.map_ramps:
            for p in ramp.points:
                h2 = self.get_terrain_z_height(p)
                pos = Point3((p.x, p.y, h2))
                color = Point3((255, 0, 0))
                if p in ramp.upper:
                    color = Point3((0, 255, 0))
                if p in ramp.upper2_for_ramp_wall:
                    color = Point3((0, 255, 255))
                if p in ramp.lower:
                    color = Point3((0, 0, 255))
                self._client.debug_box2_out(pos + Point2((0.5, 0.5)), half_vertex_length=0.25, color=color)
        
def main():
    # Multiple difficulties for enemy bots available https://github.com/Blizzard/s2client-api/blob/ce2b3c5ac5d0c85ede96cef38ee7ee55714eeb2f/include/sc2api/sc2_gametypes.h#L30
    sc2.run_game(
        sc2.maps.get("AcropolisLE"),
        [Bot(Race.Terran, HellionBot()), Computer(Race.Zerg, Difficulty.VeryHard)],
        realtime=True,
    )


if __name__ == "__main__":
    main()
