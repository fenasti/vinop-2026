"""
Fill an empty shop with everything it needs to look and work right:

  * the Studio's default look (VinOp name, colours, homepage text)
  * placeholder legal pages (imprint, privacy, terms, withdrawal, shipping)
  * Chile's wine valleys with their latitudes, and common grapes
  * DEMO wineries and wines (all invented: replace them before launch)

Safe to run more than once: it only adds what's missing.

    python manage.py seed_demo              # everything
    python manage.py seed_demo --no-wines   # just pages, regions and grapes
"""

from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand

from catalog.models import Grape, Region, Wine, Winery
from core.models import LegalPage
from studio.models import SiteSettings

# Chile's main wine valleys, north to south: (name, degrees south, description)
REGIONS = [
    (
        "Elqui",
        "30.0",
        "Desert valley under the clearest skies on earth. High-altitude vineyards, intense sun, cold nights.",
    ),
    ("Limarí", "30.6", "Limestone soils and morning fog from the Pacific: Chile's home of tense, mineral Chardonnay."),
    ("Aconcagua", "32.8", "Warm inland valley at the foot of South America's highest peak."),
    ("Casablanca", "33.3", "Cool coastal valley between Santiago and Valparaíso, made for white wine and Pinot Noir."),
    ("San Antonio", "33.6", "Vineyards a few kilometres from the ocean. Salty breezes, crisp acidity."),
    ("Maipo", "33.7", "Santiago's own valley and the classic address for Chilean Cabernet Sauvignon."),
    ("Cachapoal", "34.3", "Northern half of the Rapel valley, running from the Andes towards the coast."),
    ("Colchagua", "34.6", "Warm, generous red wine country and the heart of Carménère."),
    ("Curicó", "35.0", "Large, varied valley with a long history of white and red wines."),
    ("Maule", "35.5", "Old, dry-farmed bush vines of Carignan and País, some well over a century old."),
    ("Itata", "36.5", "Granite hills, small family growers and Chile's oldest vineyards: Cinsault and Moscatel."),
    ("Bío-Bío", "37.3", "Cooler and rainier: aromatic whites and fresh Pinot Noir."),
    ("Malleco", "38.1", "The southern frontier of Chilean wine, cool and wet, with fine Pinot Noir and Chardonnay."),
]

GRAPES = [
    "Cabernet Franc",
    "Cabernet Sauvignon",
    "Carignan",
    "Carménère",
    "Chardonnay",
    "Cinsault",
    "Malbec",
    "Moscatel de Alejandría",
    "País",
    "Pedro Jiménez",
    "Pinot Noir",
    "Riesling",
    "Sauvignon Blanc",
    "Syrah",
]

# DEMO wineries — invented names, not real producers.
WINERIES = [
    ("Estrella del Valle", "Elqui", "A family estate at 1,800 m, farming between cactus and stars."),
    ("Niebla Costera", "Limarí", "Small cellar working only limestone parcels touched by the coastal fog."),
    ("Bruma de Casablanca", "Casablanca", "Cool-climate growers making bright, early-picked wines."),
    ("Acantilado", "San Antonio", "Vineyards on the cliffs above the Pacific."),
    ("Los Tilos del Maipo", "Maipo", "Third-generation Cabernet growers in the Alto Maipo foothills."),
    ("Hacienda Las Chilcas", "Colchagua", "An old hacienda devoted to Carménère and Andean blends."),
    ("Secano Viejo", "Maule", "Rescues abandoned dry-farmed vineyards and works them by horse."),
    ("Lomas de Itata", "Itata", "A cooperative of twelve families on the granite hills of Itata."),
    ("Ribera Austral", "Bío-Bío", "Riverside vineyards with long, cool ripening seasons."),
    ("Lluvia del Sur", "Malleco", "Pioneers of the rainy south."),
]

# (winery, name, style, vintage, grapes, price, previous price, stock, alcohol, ml, featured, pairing, serve, description)
WINES = [
    (
        "Estrella del Valle",
        "Altura Syrah",
        "red",
        2021,
        ["Syrah"],
        "24.90",
        None,
        36,
        "14.0",
        750,
        True,
        "Lamb, grilled vegetables",
        "16–18 °C",
        "Dark fruit, black pepper and a cool, stony finish from high-altitude vines.",
    ),
    (
        "Estrella del Valle",
        "Desierto Blanco",
        "white",
        2023,
        ["Pedro Jiménez"],
        "16.50",
        None,
        24,
        "12.5",
        750,
        False,
        "Ceviche, goat's cheese",
        "8–10 °C",
        "Citrus, white flowers and a salty edge. Proof the desert can make fresh white wine.",
    ),
    (
        "Niebla Costera",
        "Camanchaca Chardonnay",
        "white",
        2022,
        ["Chardonnay"],
        "21.00",
        None,
        30,
        "13.0",
        750,
        True,
        "Roast chicken, scallops",
        "10–12 °C",
        "Tense and mineral, with lemon curd and a chalky finish from limestone soils.",
    ),
    (
        "Bruma de Casablanca",
        "Sauvignon Blanc",
        "white",
        2024,
        ["Sauvignon Blanc"],
        "13.90",
        None,
        60,
        "12.5",
        750,
        False,
        "Asparagus, sushi, salads",
        "7–9 °C",
        "Lime, passion fruit and fresh-cut grass. Light, crisp and very drinkable.",
    ),
    (
        "Bruma de Casablanca",
        "Pinot Noir Reserva",
        "red",
        2022,
        ["Pinot Noir"],
        "19.50",
        None,
        18,
        "13.0",
        750,
        False,
        "Duck, mushroom risotto",
        "14–16 °C",
        "Red cherry and forest floor with silky tannins.",
    ),
    (
        "Acantilado",
        "Rosé de Pinot",
        "rose",
        2024,
        ["Pinot Noir"],
        "15.90",
        None,
        40,
        "12.0",
        750,
        False,
        "Salmon, summer evenings",
        "8–10 °C",
        "Pale and dry, with strawberry, grapefruit and sea breeze.",
    ),
    (
        "Acantilado",
        "Brut Nature",
        "sparkling",
        None,
        ["Chardonnay", "Pinot Noir"],
        "27.00",
        None,
        20,
        "12.0",
        750,
        False,
        "Oysters, aperitif",
        "6–8 °C",
        "Traditional method, no added sugar. Green apple, brioche and fine bubbles.",
    ),
    (
        "Los Tilos del Maipo",
        "Gran Reserva Cabernet Sauvignon",
        "red",
        2020,
        ["Cabernet Sauvignon"],
        "29.90",
        "34.00",
        28,
        "14.0",
        750,
        True,
        "Steak, aged cheeses",
        "16–18 °C",
        "Cassis, mint and graphite: classic Alto Maipo Cabernet, ready now or in ten years.",
    ),
    (
        "Los Tilos del Maipo",
        "Cordillera Cabernet Franc",
        "red",
        2021,
        ["Cabernet Franc"],
        "22.00",
        None,
        4,
        "13.5",
        750,
        False,
        "Roast pork, lentils",
        "15–17 °C",
        "Raspberry, violets and a herbal lift.",
    ),
    (
        "Hacienda Las Chilcas",
        "Carménère Reserva",
        "red",
        2022,
        ["Carménère"],
        "14.90",
        None,
        80,
        "13.5",
        750,
        True,
        "Empanadas, chilli con carne",
        "16–18 °C",
        "Chile's signature grape: plum, red pepper and soft spice.",
    ),
    (
        "Hacienda Las Chilcas",
        "Ensamblaje Andino",
        "red",
        2019,
        ["Carménère", "Cabernet Sauvignon", "Syrah"],
        "38.00",
        None,
        12,
        "14.5",
        750,
        False,
        "Slow-cooked beef, game",
        "17–18 °C",
        "A deep, layered blend aged 18 months in French oak.",
    ),
    (
        "Secano Viejo",
        "Carignan de Secano",
        "red",
        2021,
        ["Carignan"],
        "23.50",
        None,
        22,
        "13.5",
        750,
        True,
        "Charcuterie, pizza",
        "15–17 °C",
        "From 70-year-old dry-farmed bush vines. Juicy, wild and full of energy.",
    ),
    (
        "Secano Viejo",
        "País Campesino",
        "red",
        2023,
        ["País"],
        "12.90",
        None,
        50,
        "12.0",
        750,
        False,
        "Picnics, grilled sausages",
        "12–14 °C",
        "Light, rustic and fun. Chill it slightly.",
    ),
    (
        "Lomas de Itata",
        "Cinsault",
        "red",
        2023,
        ["Cinsault"],
        "15.50",
        None,
        35,
        "12.5",
        750,
        False,
        "Tapas, roast chicken",
        "13–15 °C",
        "Bright red fruit and a floral perfume from granite soils.",
    ),
    (
        "Lomas de Itata",
        "Moscatel Naranjo",
        "orange",
        2022,
        ["Moscatel de Alejandría"],
        "18.90",
        None,
        16,
        "12.0",
        750,
        False,
        "Curries, spiced dishes",
        "10–12 °C",
        "Skin-fermented Moscatel: orange peel, tea and a gentle grip.",
    ),
    (
        "Ribera Austral",
        "Riesling",
        "white",
        2023,
        ["Riesling"],
        "17.90",
        None,
        0,
        "11.5",
        750,
        False,
        "Thai food, smoked fish",
        "8–10 °C",
        "Lime, green apple and a zip of acidity. Sold out until the next shipment.",
    ),
    (
        "Lluvia del Sur",
        "Pinot Noir Austral",
        "red",
        2022,
        ["Pinot Noir"],
        "31.00",
        None,
        14,
        "12.5",
        750,
        True,
        "Salmon, mushrooms",
        "14–16 °C",
        "Fine, fragrant and cool: the southern edge of Chilean Pinot Noir.",
    ),
    (
        "Lluvia del Sur",
        "Late Harvest Sauvignon Blanc",
        "sweet",
        2021,
        ["Sauvignon Blanc"],
        "19.90",
        None,
        20,
        "11.0",
        375,
        False,
        "Blue cheese, fruit tarts",
        "8–10 °C",
        "Honey, apricot and candied lemon. Half bottle.",
    ),
]

TODO = (
    "TODO: placeholder text. Replace it with wording checked by a lawyer before the shop goes live. "
    "Selling to consumers in Germany, these pages may need to be in German."
)


def legal_pages():
    flat = settings.SHIPPING_FLAT_RATE
    free = settings.FREE_SHIPPING_THRESHOLD
    return [
        (
            "imprint",
            "Imprint",
            1,
            f"{TODO}\n\nProvider information (§ 5 DDG): company name and legal form, address, who represents it, "
            "email and phone, commercial register number and VAT ID.",
        ),
        (
            "privacy",
            "Privacy policy",
            2,
            f"{TODO}\n\nWhat we collect (name, address, email, phone, order history), why, how long we keep it, "
            "who processes it for us (Stripe for payments, our email provider, our hosting), and the visitor's GDPR rights.\n\n"
            "This shop sets only the cookies it needs: the session and security cookies, and one cookie remembering "
            "that the visitor confirmed being 18 or older.",
        ),
        (
            "terms",
            "Terms and conditions",
            3,
            f"{TODO}\n\nWho the contract is with, how it is formed (when you click “Buy now”), prices incl. VAT, "
            "payment, delivery, age requirement (18+), retention of title, warranty.",
        ),
        (
            "withdrawal",
            "Right of withdrawal",
            4,
            f"{TODO}\n\nConsumers may withdraw from the contract within 14 days without giving a reason. "
            "Include the official model withdrawal form.",
        ),
        (
            "shipping",
            "Shipping and delivery",
            5,
            f"We deliver to {len(settings.SHIPPING_COUNTRIES)} countries in the European Union.\n\n"
            f"Delivery costs €{flat} per order and is free from €{free}.\n\n"
            "Wine is only handed to adults: the courier may ask for ID.\n\n"
            "TODO: add delivery times per country and your carrier.",
        ),
    ]


class Command(BaseCommand):
    help = "Create the default look, legal pages, Chilean regions and grapes, and demo wines."

    def add_arguments(self, parser):
        parser.add_argument("--no-wines", action="store_true", help="Skip the demo wineries and wines.")

    def handle(self, *args, no_wines=False, **options):
        SiteSettings.load()
        self.stdout.write("Studio defaults ready.")

        for slug, title, position, body in legal_pages():
            LegalPage.objects.get_or_create(slug=slug, defaults={"title": title, "position": position, "body": body})
        self.stdout.write("Legal pages ready (placeholder text marked TODO).")

        regions = {}
        for name, latitude, description in REGIONS:
            regions[name], _created = Region.objects.get_or_create(
                name=name, defaults={"latitude": Decimal(latitude), "description": description}
            )
        grapes = {name: Grape.objects.get_or_create(name=name)[0] for name in GRAPES}
        self.stdout.write(f"{len(regions)} regions and {len(grapes)} grapes ready.")

        if no_wines:
            return

        wineries = {}
        for name, region, description in WINERIES:
            wineries[name], _created = Winery.objects.get_or_create(
                name=name, defaults={"region": regions[region], "description": description}
            )

        created = 0
        for row in WINES:
            (
                winery,
                name,
                style,
                vintage,
                grape_names,
                price,
                was,
                stock,
                alcohol,
                volume,
                featured,
                pairing,
                serve,
                description,
            ) = row
            wine, is_new = Wine.objects.get_or_create(
                winery=wineries[winery],
                name=name,
                vintage=vintage,
                defaults={
                    "style": style,
                    "region": wineries[winery].region,
                    "price": Decimal(price),
                    "compare_at_price": Decimal(was) if was else None,
                    "stock": stock,
                    "alcohol": Decimal(alcohol),
                    "volume_ml": volume,
                    "is_featured": featured,
                    "food_pairing": pairing,
                    "serving_temperature": serve,
                    "description": description,
                },
            )
            if is_new:
                wine.grapes.set([grapes[g] for g in grape_names])
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{created} demo wines added. They're invented: edit or delete them at /team/wines/ before launch."
            )
        )
