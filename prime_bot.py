from sc2.bot_ai import BotAI
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2
from sc2.unit import Unit
from typing import List, Tuple


class PrimeBot(BotAI):  # inherits from BotAI (part of BurnySC2)
    def select_target(self) -> Tuple[Point2, bool, bool, bool]:
        """Select an enemy target the units should attack."""
        targets = self.enemy_structures
        if targets:
            return targets.random.position, False, False, True

        targets = self.enemy_units
        if targets:
            for target in targets:
                if target.is_flying:
                    return targets.random.position, False, True, False
            return targets.random.position, True, False, False

        if (
            self.units
            and min(
                [
                    u.position.distance_to(self.enemy_start_locations[0])
                    for u in self.units
                ]
            )
            < 5
        ):
            return self.enemy_start_locations[0].position, False, False, False

        return self.mineral_field.random.position, False, False, False

    async def on_step(
        self, iteration: int
    ):  # on_step is a method that is called every step of the game.
        async def build_structure(self, structure: UnitTypeId, ref: Unit):
            await self.build(
                structure, near=ref.position.towards(self.game_info.map_center, 5)
            )
            return

        # Finds places to build Add-ons
        def struct_points_to_build_addon(struct_position: Point2) -> List[Point2]:
            """Return all points that need to be checked when trying to build an addon. Returns 4 points."""
            addon_offset: Point2 = Point2((2.5, -0.5))
            addon_position: Point2 = struct_position + addon_offset
            addon_points = [
                (addon_position + Point2((x - 0.5, y - 0.5))).rounded
                for x in range(0, 2)
                for y in range(0, 2)
            ]
            return addon_points

        def struct_land_positions(struct_position: Point2) -> List[Point2]:
            """Return all points that need to be checked when trying to land at a location where there is enough space to build an addon. Returns 13 points."""
            land_positions = [
                (struct_position + Point2((x, y))).rounded
                for x in range(-1, 2)
                for y in range(-1, 2)
            ]
            return land_positions + struct_points_to_build_addon(struct_position)

        async def struct_build_addon(
            self, struct_type: UnitTypeId, addon_type: UnitTypeId
        ):
            struct: Unit
            for struct in self.structures(struct_type).ready.idle:
                if not struct.has_add_on and self.can_afford(addon_type):
                    addon_points = struct_points_to_build_addon(struct.position)
                    if all(
                        self.in_map_bounds(addon_point)
                        and self.in_placement_grid(addon_point)
                        and self.in_pathing_grid(addon_point)
                        for addon_point in addon_points
                    ):
                        struct.build(addon_type)
                    else:
                        struct(AbilityId.LIFT)

        async def struct_land(self, struct_type: UnitTypeId):
            for struct in self.structures(struct_type).idle:
                possible_land_positions_offset = sorted(
                    (Point2((x, y)) for x in range(-10, 10) for y in range(-10, 10)),
                    key=lambda point: point.x**2 + point.y**2,
                )
                offset_point: Point2 = Point2((-0.5, -0.5))
                possible_land_positions = (
                    struct.position.rounded + offset_point + p
                    for p in possible_land_positions_offset
                )
                for target_land_position in possible_land_positions:
                    land_and_addon_points: List[Point2] = struct_land_positions(
                        target_land_position
                    )
                    if all(
                        self.in_map_bounds(land_pos)
                        and self.in_placement_grid(land_pos)
                        and self.in_pathing_grid(land_pos)
                        for land_pos in land_and_addon_points
                    ):
                        struct(AbilityId.LAND, target_land_position)
                        break

        # Buildings
        armories = self.structures(UnitTypeId.ARMORY)
        factories = self.structures(UnitTypeId.FACTORY) + self.structures(
            UnitTypeId.FACTORYFLYING
        )

        if not self.townhalls:
            # Attack with all workers if we don't have any nexuses left, attack-move on enemy spawn (doesn't work on 4 player map) so that probes auto attack on the way
            for worker in self.workers:
                worker.attack(self.enemy_start_locations[0])
            return
        else:
            cc = self.townhalls.random

        # Make workers until we have 24 total or at least 8 per Command Center
        if (
            self.supply_workers < 24
            or self.supply_workers < (self.townhalls.amount * 8)
        ) and cc.is_idle:
            if self.can_afford(UnitTypeId.SCV):
                cc.train(UnitTypeId.SCV)

        # If we have no Barracks, build one near starting Town
        elif (
            not self.structures(UnitTypeId.BARRACKS)
            and not self.structures(UnitTypeId.BARRACKSREACTOR)
            and not self.structures(UnitTypeId.BARRACKSFLYING)
            and self.already_pending(UnitTypeId.BARRACKS) == 0
        ):
            if self.can_afford(UnitTypeId.BARRACKS):
                await self.build(
                    UnitTypeId.BARRACKS,
                    near=cc.position.towards(self.game_info.map_center, 8),
                )

        # If we have no Engineering Bay, build one near Command Center
        elif not self.structures(UnitTypeId.ENGINEERINGBAY):
            await build_structure(self, UnitTypeId.ENGINEERINGBAY, cc)

        # If we have no Missile Turrets, build one near Command Center
        elif self.structures(UnitTypeId.MISSILETURRET).amount < 2:
            await build_structure(self, UnitTypeId.MISSILETURRET, cc)

        # If we have a Barracks and can afford Marines, train until 12
        elif self.structures(UnitTypeId.BARRACKS) and self.can_afford(
            UnitTypeId.MARINE
        ):
            for rax in self.structures(UnitTypeId.BARRACKS):
                if (
                    self.can_afford(UnitTypeId.MARINE)
                    and self.structures(UnitTypeId.BARRACKSREACTOR)
                    and self.units(UnitTypeId.MARINE).amount < 10
                ):
                    rax.train(UnitTypeId.MARINE)

            # Build refineries, 2 per Command Center
            if self.structures(UnitTypeId.BARRACKS) and self.gas_buildings.amount < (
                2 * self.townhalls.amount
            ):
                if self.can_afford(UnitTypeId.REFINERY):
                    vgs = self.vespene_geyser.closer_than(20, cc)
                    for vg in vgs:
                        if self.gas_buildings.filter(
                            lambda unit: unit.distance_to(vg) < 1
                        ):
                            break
                        worker: Unit = self.select_build_worker(vg.position)
                        if worker is None:
                            break
                        worker.build(UnitTypeId.REFINERY, vg)
                        break

            # Build Factory if we dont have one
            if self.tech_requirement_progress(UnitTypeId.FACTORY) == 1:
                if factories.amount < 2:
                    if self.can_afford(UnitTypeId.FACTORY):
                        await self.build(
                            UnitTypeId.FACTORY,
                            near=cc.position.towards(self.game_info.map_center, 8),
                        )
                # Build Starport once we can build Starports, up to 2
                elif (
                    factories.ready
                    and self.structures.of_type(
                        {UnitTypeId.STARPORT, UnitTypeId.STARPORTFLYING}
                    ).ready.amount
                    + self.already_pending(UnitTypeId.STARPORT)
                    < 2
                ):
                    if self.can_afford(UnitTypeId.STARPORT):
                        await self.build(
                            UnitTypeId.STARPORT,
                            near=cc.position.towards(self.game_info.map_center, 10),
                        )

            # Build Armory, if we dont have one
            if self.tech_requirement_progress(UnitTypeId.ARMORY) == 1:
                if armories.amount < 1:
                    if self.can_afford(UnitTypeId.ARMORY):
                        await self.build(
                            UnitTypeId.ARMORY,
                            near=cc.position.towards(self.game_info.map_center, 7),
                        )

            # Build Fusion Core, if we don't have one
            if self.structures(UnitTypeId.STARPORT).ready:
                if (
                    self.can_afford(UnitTypeId.FUSIONCORE)
                    and not self.structures(UnitTypeId.FUSIONCORE)
                    and self.already_pending(UnitTypeId.FUSIONCORE) == 0
                ):
                    await self.build(
                        UnitTypeId.FUSIONCORE,
                        near=cc.position.towards(self.game_info.map_center, 7),
                    )

        # ----------------------------------------------ARMORY BEHAVIOUR----------------------------------------------------------

        # ----------------------------------------------FACTORY BEHAVIOUR----------------------------------------------------------
        await struct_build_addon(self, UnitTypeId.FACTORY, UnitTypeId.FACTORYTECHLAB)
        await struct_land(self, UnitTypeId.FACTORYFLYING)

        # Build more Siege Tanks
        if (
            self.structures(UnitTypeId.FACTORY)
            and (self.can_afford(UnitTypeId.SIEGETANK))
            and self.units(UnitTypeId.SIEGETANK).amount < 8
        ):
            for fact in self.structures(UnitTypeId.FACTORY).idle:
                if fact.has_add_on:
                    if not self.can_afford(UnitTypeId.SIEGETANK):
                        break
                    fact.train(UnitTypeId.SIEGETANK)

        # ----------------------------------------------STARPORT BEHAVIOUR--------------------------------------------------------
        await struct_build_addon(self, UnitTypeId.STARPORT, UnitTypeId.STARPORTTECHLAB)
        await struct_land(self, UnitTypeId.STARPORTFLYING)

        # Train more Battlecruisers
        if self.structures(UnitTypeId.FUSIONCORE) and self.can_afford(
            UnitTypeId.BATTLECRUISER
        ):
            for sp in self.structures(UnitTypeId.STARPORT).idle:
                if sp.has_add_on:
                    if not self.can_afford(UnitTypeId.BATTLECRUISER):
                        break
                    sp.train(UnitTypeId.BATTLECRUISER)

        # ----------------------------------------------BARRACKS BEHAVIOUR--------------------------------------------------------
        await struct_build_addon(self, UnitTypeId.BARRACKS, UnitTypeId.BARRACKSREACTOR)
        await struct_land(self, UnitTypeId.BARRACKSFLYING)

        # ----------------------------------------------MILITARY UNIT BEHAVIOUR---------------------------------------------------
        bcs = self.units(UnitTypeId.BATTLECRUISER)
        marines = self.units(UnitTypeId.MARINE)
        sts = self.units(UnitTypeId.SIEGETANK) + self.units(UnitTypeId.SIEGETANKSIEGED)

        # BATTLECRUISERS:
        # --------------------------------------------
        # OFFENSIVE
        # Send all BCs to attack a target.
        if bcs and bcs.amount >= 2:
            (
                target,
                target_is_gnd_enemy_unit,
                target_is_fly_enemy_unit,
                target_is_enemy_struct,
            ) = self.select_target()
            bc: Unit
            for bc in bcs:
                # Order the BC to attack-move flying units first
                if target_is_fly_enemy_unit and (bc.is_idle or bc.is_moving):
                    bc.attack(target)
                # Order the BC to attack-move the target
                elif (target_is_gnd_enemy_unit or target_is_enemy_struct) and (
                    bc.is_idle or bc.is_moving
                ):
                    bc.attack(target)
                # Order the BC to move to the target, and once the select_target returns an attack-target, change it to attack-move
                elif bc.is_idle:
                    bc.move(target)

        # MARINES:
        # --------------------------------------------
        # Selects all units of each type

        # OFFENSIVE
        # Send all Marines to attack a target
        if marines and marines.amount >= 6 and sts.amount >= 5:
            (
                target,
                target_is_gnd_enemy_unit,
                target_is_fly_enemy_unit,
                target_is_enemy_struct,
            ) = self.select_target()
            marine: Unit
            for marine in marines:
                # Order the Marines to attack-move the target
                if (target_is_gnd_enemy_unit or target_is_fly_enemy_unit) and (
                    marine.is_idle or marine.is_moving
                ):
                    marine.attack(target)
                # Order the Marines to move to the target, and once the select_target returns an attack-target, change it to attack-move
                elif marine.is_idle:
                    marine.move(target)
        # DEFENSIVE
        # # If we have Marines, build 2 Bunkers
        if self.units(UnitTypeId.MARINE):
            if (
                self.can_afford(UnitTypeId.BUNKER)
                and self.structures(UnitTypeId.BUNKER).amount < 2
                and self.already_pending(UnitTypeId.BUNKER) == 0
            ):
                await self.build(
                    UnitTypeId.BUNKER,
                    near=cc.position.towards(self.game_info.map_center, 12),
                )

        # Fill bunkers with Marines, if there are bunkers with room
        if self.structures(UnitTypeId.BUNKER).amount > 0:
            for bunker in self.structures(UnitTypeId.BUNKER):
                if bunker.cargo_left > 0:
                    for unit in self.units(UnitTypeId.MARINE):
                        bunker(AbilityId.LOAD_BUNKER, unit)

        # OFFENSIVE
        # Send all Siege Tanks to attack a target
        if sts and sts.amount >= 5 and marines.amount >= 6:
            (
                target,
                target_is_gnd_enemy_unit,
                target_is_fly_enemy_unit,
                target_is_enemy_struct,
            ) = self.select_target()
            st: Unit
            for st in sts:
                # Order the Siege Tank to attack-move the target
                if (target_is_gnd_enemy_unit or target_is_fly_enemy_unit) and (
                    st.is_idle or st.is_moving
                ):
                    st.attack(target)
                elif target_is_enemy_struct and (st.is_idle or st.is_moving):
                    st.attack(target)
                # Order the Siege Tank to move to the target, and once the select_target returns an attack-target, change it to attack-move
                elif st.is_idle:
                    st(AbilityId.UNSIEGE_UNSIEGE)
                    st.move(target)
        # ----------------------------------------------MAINTENANCE-----------------------------------------------------------------

        # SUPPLY
        # Build more supply depots
        if (
            self.supply_left < 6
            and self.supply_used >= 14
            and not self.already_pending(UnitTypeId.SUPPLYDEPOT)
        ):
            if self.can_afford(UnitTypeId.SUPPLYDEPOT):
                await self.build(
                    UnitTypeId.SUPPLYDEPOT,
                    near=cc.position.towards(self.game_info.map_center, 8),
                )

        # Lowers all supply depots
        for depot in self.structures(UnitTypeId.SUPPLYDEPOT):
            depot(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        # VESPENE GAS
        # Saturate refineries
        for refinery in self.gas_buildings:
            if refinery.assigned_harvesters < refinery.ideal_harvesters:
                worker = self.workers.closer_than(10, refinery)
                if worker:
                    worker.random.gather(refinery)

        # MINERALS
        # Send workers back to mine if they are idle
        for scv in self.workers.idle:
            scv.gather(self.mineral_field.closest_to(cc))

        # If too many workers are idle, start expanding
        if self.workers.idle.amount > 4:
            await self.expand_now()
