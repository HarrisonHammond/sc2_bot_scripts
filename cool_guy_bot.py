import random
from sc2.bot_ai import BotAI
from sc2.data import Difficulty, Race, Alert
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.buff_id import BuffId
from sc2.position import Point2, Point3


async def build_building(
    self,
    nexus,
    building_type,
    building_limit,
    placement_location=None,
    position=None,
    required_distance=None,
):
    """
    Builds the specified building if we have enough minerals and
    the building is not already in progress.
    self: the bot
    nexus: the nexus to base the building from
    building_type: the type of building to build
    building_limit: the maximum amount of buildings of this type to build
    placement_location: the rough area to place the building
    position: the exact position to place the building
    required_distance: the minimum distance required between buildings
    """
    # if we can afford the building and have available workers, build one
    if (
        self.can_afford(building_type)
        and (self.workers.idle.amount + self.workers.gathering.amount) > 0
    ):
        if placement_location is None:
            if position is None:
                placement_position = await self.find_placement(
                    building_type,
                    near=nexus.position.towards(
                        self.enemy_start_locations[0], random.randint(3, 10)
                    ),
                    placement_step=1,
                )
            else:
                placement_position = await self.find_placement(
                    building_type,
                    near=position,
                    placement_step=1,
                )

            # # if there is a required_distance then ensure there are
            # # x square between the building and other buildings of type
            # if (
            #     required_distance is not None
            #     and self.structures(building_type).amount > 0
            # ):
            #     while (
            #         self.structures(building_type)
            #         .sorted_by_distance_to(placement_position)[0]
            #         .position
            #         < required_distance
            #     ):
            #         placement_position[0] += 1
            #         placement_position[1] += 1

        # get someone to build the structure
        if self.workers.idle.amount > 0:
            builders = self.workers.idle
        else:
            builders = self.workers.gathering

        # if the structure and builder are valid, build the structure
        if (
            placement_position
            and builders
            and self.already_pending(building_type)
            + self.structures.filter(
                lambda structure: structure.type_id == building_type
                and structure.is_ready
            ).amount
            < building_limit
        ):
            build_worker = builders.closest_to(placement_position)
            self.do(build_worker.build(building_type, placement_position))
            return True
    return False


async def build_unit(self, nexus, unit_type, ability_type=None, unit_limit=10):
    # build the unit if we have enough minerals and there are less than the limit
    if (
        self.can_afford(unit_type)
        and self.already_pending(unit_type) + self.units(unit_type).amount < unit_limit
        and self.units(unit_type).amount < unit_limit
        and self.larva.amount > 0
    ):
        if unit_type != UnitTypeId.QUEEN:
            my_larva = self.larva.random
            my_larva(ability_type)
        else:
            nexus.build(unit_type)
        return True
    return False


async def build_upgrade(self, upgrade_id, upgrade_building_id):
    if (
        self.can_afford(upgrade_id)
        and self.structures(upgrade_building_id).amount > 0
        and self.time > 60 * 6
    ):
        self.do(self.structures(upgrade_building_id).random.research(upgrade_id))


async def check_buildings(self, nexus):
    # check if we can afford each building, then do so if we can
    if nexus.is_ready:
        tower_distance = 20
        position = nexus.position.towards(
            self.enemy_start_locations[0], random.randint(5, 10)
        )

        # get tower count
        towers = self.structures(UnitTypeId.SPORECRAWLER).filter(
            lambda s: s.distance_to(nexus) < tower_distance
        )
        pending_towers = (
            towers
            - self.structures(UnitTypeId.SPORECRAWLER)
            .filter(lambda s: s.distance_to(nexus) < tower_distance)
            .ready
        )

        # build defensive structures if we have enough minerals
        # they should have a minimum of 5 within 10 distance of each nexus
        if self.structures(UnitTypeId.SPORECRAWLER).amount > 0:
            if (towers.amount + pending_towers.amount) < 2:
                await build_building(
                    self,
                    nexus,
                    UnitTypeId.SPORECRAWLER,
                    20,
                    position=position,
                    required_distance=5,
                )
        else:
            await build_building(
                self,
                nexus,
                UnitTypeId.SPORECRAWLER,
                5,
                position=position,
                required_distance=5,
            )

        # get tower count
        towers = self.structures(UnitTypeId.SPINECRAWLER).filter(
            lambda s: s.distance_to(nexus) < tower_distance
        )
        pending_towers = (
            towers
            - self.structures(UnitTypeId.SPINECRAWLER)
            .filter(lambda s: s.distance_to(nexus) < tower_distance)
            .ready
        )

        # build defensive structures if we have enough minerals
        # they should have a minimum of 5 within 10 distance of each nexus
        if self.structures(UnitTypeId.SPINECRAWLER).amount > 0:
            if (towers.amount + pending_towers.amount) < 5:
                await build_building(
                    self,
                    nexus,
                    UnitTypeId.SPINECRAWLER,
                    20,
                    position=position,
                    required_distance=5,
                )
        else:
            await build_building(
                self,
                nexus,
                UnitTypeId.SPINECRAWLER,
                5,
                position=position,
                required_distance=5,
            )

    await build_building(self, nexus, UnitTypeId.EVOLUTIONCHAMBER, 1)
    # await build_building(self, nexus, UnitTypeId.SPIRE, 1)
    await build_building(self, nexus, UnitTypeId.ULTRALISKCAVERN, 1)
    # await build_building(self, nexus, UnitTypeId.BANELINGNEST, 1)
    # await build_building(self, nexus, UnitTypeId.ROACHWARREN, 1)
    # await build_building(self, nexus, UnitTypeId.HYDRALISKDEN, 1)
    await build_building(self, nexus, UnitTypeId.INFESTATIONPIT, 1)
    await build_building(self, nexus, UnitTypeId.SPAWNINGPOOL, 1)

    if (
        self.can_afford(UnitTypeId.EXTRACTOR)
        and self.structures(UnitTypeId.EXTRACTOR).closer_than(15, nexus).amount < 2
    ):
        if self.can_afford(UnitTypeId.EXTRACTOR) and not self.already_pending(
            UnitTypeId.EXTRACTOR
        ):
            await self.build(
                UnitTypeId.EXTRACTOR,
                self.vespene_geyser.closer_than(15, nexus).random,
            )


async def check_units(self, nexus):
    # determine the required amount of workers for our structures
    required_workers = 0
    for harvester in self.gas_buildings | self.townhalls:
        required_workers += harvester.ideal_harvesters

    # build more overlord's if we have enough minerals.
    # This ensures that we have enough pop cap
    if (
        self.can_afford(UnitTypeId.OVERLORD)
        and self.supply_used >= self.supply_cap - 4
        and not self.already_pending(UnitTypeId.OVERLORD) > 1
        and self.larva.amount > 0
    ):
        await build_unit(
            self,
            nexus,
            UnitTypeId.OVERLORD,
            AbilityId.LARVATRAIN_OVERLORD,
            unit_limit=25,
        )

    # build workers if we have enough minerals, then assign them to the nexus
    # if we have too many workers, expand
    if (
        self.can_afford(UnitTypeId.DRONE)
        and self.workers.amount < required_workers
        and self.larva.amount > 0
        # and self.workers.amount < 60
        # and self.time > 60 * 7
    ):
        my_larva = self.larva.random
        my_larva(AbilityId.LARVATRAIN_DRONE)

    # build queens
    await build_unit(self, nexus, UnitTypeId.QUEEN, unit_limit=2)

    # ensure we have an ULTRALISKCAVERN before we build anything else
    if self.structures(UnitTypeId.ULTRALISKCAVERN).amount > 0:
        # build spawning pool units
        await build_unit(
            self,
            nexus,
            UnitTypeId.ULTRALISK,
            AbilityId.LARVATRAIN_ULTRALISK,
            unit_limit=20,
        )

    # build swarm hosts if possible
    if self.structures(UnitTypeId.INFESTATIONPIT).ready.amount > 0:
        # build spawning pool units
        if self.can_afford(UnitTypeId.SWARMHOSTMP):
            self.train(UnitTypeId.SWARMHOSTMP)

    # ensure we have a spawning pool before we build anything else
    if self.structures(UnitTypeId.SPAWNINGPOOL).amount > 0:
        # build spawning pool units
        await build_unit(
            self,
            nexus,
            UnitTypeId.ROACH,
            AbilityId.LARVATRAIN_ROACH,
            unit_limit=12,
        )

        if (self.time < zerg_rush_time_limit) or (
            self.units(UnitTypeId.ZERGLING).amount
            + self.units(UnitTypeId.BANELING).amount
            < 10
        ):
            await build_unit(
                self,
                nexus,
                UnitTypeId.ZERGLING,
                AbilityId.LARVATRAIN_ZERGLING,
                unit_limit=12,
            )


async def check_upgrades(self, nexus):
    # general zerg upgrades
    await build_upgrade(
        self, UpgradeId.ZERGGROUNDARMORSLEVEL2, UnitTypeId.EVOLUTIONCHAMBER
    )
    await build_upgrade(
        self, UpgradeId.ZERGMELEEWEAPONSLEVEL2, UnitTypeId.EVOLUTIONCHAMBER
    )
    await build_upgrade(
        self, UpgradeId.ZERGGROUNDARMORSLEVEL1, UnitTypeId.EVOLUTIONCHAMBER
    )
    await build_upgrade(
        self, UpgradeId.ZERGMELEEWEAPONSLEVEL1, UnitTypeId.EVOLUTIONCHAMBER
    )
    await build_upgrade(self, UpgradeId.CHITINOUSPLATING, UnitTypeId.ULTRALISKCAVERN)
    await build_upgrade(self, UpgradeId.ANABOLICSYNTHESIS, UnitTypeId.ULTRALISKCAVERN)
    await build_upgrade(self, UpgradeId.ZERGLINGMOVEMENTSPEED, UnitTypeId.SPAWNINGPOOL)
    await build_upgrade(self, UpgradeId.ZERGLINGATTACKSPEED, UnitTypeId.SPAWNINGPOOL)

    # upgrade spire if possible
    if (
        self.can_afford(UnitTypeId.GREATERSPIRE)
        and self.structures(UnitTypeId.SPIRE).amount > 0
    ):
        await self.build(UnitTypeId.GREATERSPIRE, near=nexus.position)


# build a zerg rush bot
class CoolGuyBot(BotAI):
    global zerg_rush_time_limit
    zerg_rush_time_limit = 60 * 8

    async def on_step(
        self, iteration: int
    ):  # on_step is a method that is called every step of the game.
        if self.townhalls:

            # grab a random nexus
            if self.townhalls.idle.amount > 0:
                nexus = self.townhalls.idle.random
            elif self.townhalls.ready.amount > 0:
                nexus = self.townhalls.ready.random
            else:
                nexus = self.townhalls.random

            # # if we have idle workers assign workers
            # if ((self.workers.idle.amount > 0) or (nexus.surplus_harvesters > 0)) and (
            #     int(self.time) % 60 == 0
            # ):
            #     await self.distribute_workers()
            await self.distribute_workers()

            if self.alert(Alert.BuildingUnderAttack):
                pass

            # check the type of nexus and build the appropriate upgrade
            if (
                self.can_afford(UnitTypeId.LAIR)
                and nexus.type_id == UnitTypeId.HATCHERY
            ):
                nexus(AbilityId.UPGRADETOLAIR_LAIR)
            elif (
                self.can_afford(UnitTypeId.HIVE)
                and nexus.type_id == UnitTypeId.LAIR
                and self.structures(UnitTypeId.INFESTATIONPIT).amount > 0
            ):
                nexus(AbilityId.UPGRADETOHIVE_HIVE)

            await check_units(self, nexus)
            await check_buildings(self, nexus)
            await check_upgrades(self, nexus)

            # assign queens to jobs
            if self.units(UnitTypeId.QUEEN).idle.amount > 1:
                queen = self.units(UnitTypeId.QUEEN).idle.random
                # Inject hatchery if queen has more than 25 energy
                if queen.energy >= 25 and not nexus.has_buff(
                    BuffId.QUEENSPAWNLARVATIMER
                ):
                    queen(AbilityId.EFFECT_INJECTLARVA, nexus)

                # If all hatcheries are busy, build a creep tunnel
                elif queen.energy >= 25:
                    # build as far away from current tumor as possible
                    distance = 8

                    # # get the furthest creep tunnel from the base
                    # if self.structures(UnitTypeId.CREEPTUMORBURROWED).amount > 0:
                    #     furthest_tunnel = self.structures(
                    #         UnitTypeId.CREEPTUMORBURROWED
                    #     ).furthest_to(self.enemy_start_locations[0])
                    #     pos = furthest_tunnel.position.towards(
                    #         self.enemy_start_locations[0], distance
                    #     )
                    # else:
                    #     pos = nexus.position.towards(
                    #         self.enemy_start_locations[0], distance
                    #     )

                    # queen.build(UnitTypeId.CREEPTUMOR, pos)

            # # if we have creep tumors then have them expand
            # if self.structures(UnitTypeId.CREEPTUMORBURROWED).idle.amount > 0:
            #     current_tumors = self.structures(UnitTypeId.CREEPTUMORBURROWED).idle
            #     for tumor in current_tumors:
            #         # build as far away from current tumor as possible
            #         pos = tumor.position.towards(
            #             self.enemy_start_locations[0], random.randrange(8, 15)
            #         )
            #         await self.build(UnitTypeId.CREEPTUMOR, near=pos)

            # # upgrade zergs as soon as possible if we have a baneling nest
            # if (
            #     (self.units(UnitTypeId.ZERGLING).amount > 0)
            #     and (self.time > zerg_rush_time_limit)
            #     and (self.structures(UnitTypeId.BANELINGNEST).amount > 0)
            # ):
            #     for zerg in self.units(UnitTypeId.ZERGLING).idle:
            #         zerg(AbilityId.MORPHZERGLINGTOBANELING_BANELING)

            #### START OF COMBAT LOGIC ####
            # check if there are enemy units near the nexus
            if self.all_enemy_units.amount > 0:
                # if there are enemy units near the nexus then attack them
                if self.all_enemy_units.closer_than(20, nexus).amount > 0:
                    for unit in self.units.idle:
                        if unit.tag in self.unit_tags_received_action:
                            continue

                        # ensure we have a military unit
                        if (
                            (unit.type_id != UnitTypeId.DRONE)
                            and (unit.type_id != UnitTypeId.OVERLORD)
                            and (unit.type_id != UnitTypeId.SWARMHOSTMP)
                        ):
                            unit.attack(
                                self.all_enemy_units.closer_than(20, nexus).random
                            )
                        # if we have a swarm host, then attack the enemy with locust
                        elif unit.type_id == UnitTypeId.SWARMHOSTMP:
                            unit(
                                AbilityId.EFFECT_SPAWNLOCUSTS,
                                self.all_enemy_units.closer_than(
                                    20, nexus
                                ).random.position,
                            )
            # if we have enough zerglings, rush the enemy
            if (self.units(UnitTypeId.ZERGLING).amount >= 12) and (
                self.time < zerg_rush_time_limit
            ):
                for zerg in self.units(UnitTypeId.ZERGLING):
                    if zerg.tag in self.unit_tags_received_action:
                        continue
                    self.do(zerg.attack(self.enemy_start_locations[0]))

            # if we are past our zerg rush time limit, wait for a decent amount of other units
            elif (self.army_count >= 40) and (self.time > zerg_rush_time_limit):
                for unit in self.units:
                    if unit.tag in self.unit_tags_received_action:
                        continue

                    # if we have a host we need to keep them away from the enemy base while they summon
                    if unit.type_id == UnitTypeId.SWARMHOSTMP:
                        self.do(
                            unit.move(self.enemy_start_locations[0].towards(nexus, 30))
                        )
                        unit(
                            AbilityId.EFFECT_SPAWNLOCUSTS,
                            self.enemy_start_locations[0],
                        )

                    if (
                        (unit.type_id != UnitTypeId.QUEEN)
                        and (unit.type_id != UnitTypeId.DRONE)
                        and (unit.type_id != UnitTypeId.OVERLORD)
                        and (unit.type_id != UnitTypeId.SWARMHOSTMP)
                    ):
                        if self.enemy_structures:
                            attack_target = random.choice(
                                self.enemy_structures
                            ).position
                        else:
                            attack_target = self.enemy_start_locations[0]

                        self.do(unit.attack(attack_target))

            # # patrol the enemy bases
            # if self.units(UnitTypeId.ZERGLING).idle.amount > 0:
            #     selected_unit = self.units(UnitTypeId.ZERGLING).idle.random
            #     if selected_unit.tag not in self.unit_tags_received_action:
            #         selected_unit.patrol(
            #             self.enemy_start_locations[0].towards(self.start_location, 30)
            #         )

            # calc the total ideal workers
            total_ideal_workers = 0
            for base in self.townhalls:
                if base.is_ready:
                    total_ideal_workers += base.ideal_harvesters

            # determine if expansion is needed
            if (
                # nexus.ideal_harvesters <= 16
                (total_ideal_workers <= self.units(UnitTypeId.DRONE).amount)
                and self.townhalls.amount < 4
                and not self.already_pending(UnitTypeId.HATCHERY)
                and self.time > 60 * 4
            ):
                # if unit.tag in self.unit_tags_received_action:
                #     continue
                await self.expand_now()

        else:
            if self.can_afford(UnitTypeId.NEXUS):
                await self.expand_now()
