"""This file defines command "python manage.py init" which initialises static tables"""

from django.core.management import BaseCommand
from django.db import transaction

from Sodia.settings import BASE_DIR
from settings.models import Country, House, HouseBoardingType, YearGroup


@transaction.atomic
def init_countries(rewrite=False):
    """Add countries from "/data/countries.txt" csv file to the Country table.
    If --rewrite is set, clear old data, otherwise only add missing ids"""
    lst = []  # list of countries
    with open(BASE_DIR / "data" / "countries.txt", encoding="utf-8") as file:  # open csv file
        for line in file:
            code, _, _, name = [s.strip() for s in line.strip("| \n").split("|")]  # parse line
            lst.append((name.replace(r"\[", "(").replace(r"\]", ")"), code))
    lst.sort()  # sort countries by name
    # create Country objects
    countries = [Country(id=pk, code=code.lower(), name=name) for pk, (name, code) in enumerate(lst, start=1)]
    if rewrite:
        # clear table if --rewrite is set
        Country.objects.all().delete()
    # create new db records (ignore already existing records if --rewrite is not set)
    Country.objects.bulk_create(countries, ignore_conflicts=not rewrite)


@transaction.atomic
def init_houses(rewrite=False):
    """Add Day/Boarding Houses to the House table.
    If --rewrite is set, clear old data, otherwise only add missing ids"""
    houses = [  # create House objects
        House(id=1, name="Granville", boarding_type=HouseBoardingType.BOARDING),
        House(id=2, name="Forest", boarding_type=HouseBoardingType.BOARDING),
        House(id=3, name="Holman", boarding_type=HouseBoardingType.BOARDING),
        House(id=4, name="Robinson", boarding_type=HouseBoardingType.DAY),
        House(id=5, name="Propert", boarding_type=HouseBoardingType.DAY),
        House(id=6, name="Carr", boarding_type=HouseBoardingType.DAY),
        House(id=7, name="Fayrer", boarding_type=HouseBoardingType.DAY),
        House(id=8, name="Wilson", boarding_type=HouseBoardingType.BOARDING),
        House(id=9, name="Crawford", boarding_type=HouseBoardingType.BOARDING),
        House(id=10, name="White", boarding_type=HouseBoardingType.MIXED),
        House(id=11, name="Raven", boarding_type=HouseBoardingType.DAY),
        House(id=12, name="Rosebery", boarding_type=HouseBoardingType.DAY),
        House(id=13, name="Murrell", boarding_type=HouseBoardingType.DAY),
    ]
    if rewrite:
        # clear table if --rewrite is set
        House.objects.all().delete()
    # create new db records (ignore already existing records if --rewrite is not set)
    House.objects.bulk_create(houses, ignore_conflicts=not rewrite)


@transaction.atomic
def init_year_groups(rewrite=False):
    """Add Year Groups to the YearGroup table.
    If --rewrite is set, clear old data, otherwise only add missing ids"""
    year_groups = [  # create YearGroup objects
        YearGroup(year_group_number=9, name="Year 9"),  # Sodia is for Year 9+
        YearGroup(year_group_number=10, name="Year 10"),
        YearGroup(year_group_number=11, name="Year 11"),
        YearGroup(year_group_number=12, name="Year 12"),
        YearGroup(year_group_number=13, name="Year 13"),
    ]
    if rewrite:
        # clear table if --rewrite is set
        YearGroup.objects.all().delete()
    # create new db records (ignore already existing records if --rewrite is not set)
    YearGroup.objects.bulk_create(year_groups, ignore_conflicts=not rewrite)


class Command(BaseCommand):
    """Command class to initialise static tables"""
    help = "Initialises static tables"

    def add_arguments(self, parser):
        """add argument --rewrite to the command.
        If set, existing data in tables is cleared before new data is created.
        Otherwise, new data is added only for missing id values in the table, and no rows are removed"""
        parser.add_argument(
            "--rewrite",
            action="store_true",
            help="Erase current content",
        )

    def handle(self, *args, **options):
        """run the command"""
        init_countries(options["rewrite"])
        init_houses(options["rewrite"])
        init_year_groups(options["rewrite"])
        self.stdout.write(self.style.SUCCESS("Initialisation complete"))  # display success message
