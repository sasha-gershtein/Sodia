from django.core.management import BaseCommand
from django.db import transaction

from Sodia.settings import BASE_DIR
from settings.models import Country, House, HouseBoardingType, YearGroup


@transaction.atomic
def init_countries(rewrite=False):
    lst = []
    with open(BASE_DIR / "data" / "countries.txt", encoding="utf-8") as file:
        for line in file:
            code, _, _, name = [s.strip() for s in line.strip("| \n").split("|")]
            lst.append((name.replace(r"\[", "(").replace(r"\]", ")"), code))
    lst.sort()
    countries = [Country(id=pk, code=code.lower(), name=name) for pk, (name, code) in enumerate(lst, start=1)]
    if rewrite:
        Country.objects.all().delete()
    Country.objects.bulk_create(countries, ignore_conflicts=not rewrite)


@transaction.atomic
def init_houses(rewrite=False):
    houses = [
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
        House.objects.all().delete()
    House.objects.bulk_create(houses, ignore_conflicts=not rewrite)


@transaction.atomic
def init_year_groups(rewrite=False):
    year_groups = [
        YearGroup(year_group_number=9, name="Year 9"),
        YearGroup(year_group_number=10, name="Year 10"),
        YearGroup(year_group_number=11, name="Year 11"),
        YearGroup(year_group_number=12, name="Year 12"),
        YearGroup(year_group_number=13, name="Year 13"),
    ]
    if rewrite:
        YearGroup.objects.all().delete()
    YearGroup.objects.bulk_create(year_groups, ignore_conflicts=not rewrite)


class Command(BaseCommand):
    help = "Initialises static tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rewrite",
            action="store_true",
            help="Erase current content",
        )

    def handle(self, *args, **options):
        init_countries(options["rewrite"])
        init_houses(options["rewrite"])
        init_year_groups(options["rewrite"])
        self.stdout.write(self.style.SUCCESS("Initialisation complete"))
