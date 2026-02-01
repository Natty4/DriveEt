# core/management/commands/seed_db.py
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from core.models import (
    QuestionCategory, QuestionCategoryTranslation,
    RoadSignCategory, RoadSignCategoryTranslation,
    RoadSign, RoadSignTranslation,
    Question, QuestionTranslation,
    AnswerChoice, AnswerChoiceTranslation,
    Explanation, ExplanationTranslation,
    Exam, ExamTranslation
)
from payment.models import PaymentMethod, PaymentMethodTranslation
from users.models import SubscriptionTier, SubscriptionTierTranslation, UserProfile

from django.contrib.auth import get_user_model
User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with realistic multilingual driving exam data — fully idempotent and complete'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("Starting complete database seeding (idempotent)...")
        
        # Create admin user if not exists
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='pass'
            )
            UserProfile.objects.create(
                user=admin
            )
            self.stdout.write(self.style.SUCCESS('Admin user created.'))

        # ===================================================================
        # 1. Question Categories (idempotent)
        # ===================================================================
        q_categories = {
            'SIGN': {
                'en': "Road Signs",
                'am': "የመንገድ ምልክቶች",
                'ti': "ምልክታት መንገዲ",
                'or': "Mallattoolee Margaa"
            },
            'RULES': {
                'en': "Traffic Rules & Regulations",
                'am': "የትራፊክ ደንቦችና መመሪያዎች",
                'ti': "ስርዓተ ትራፊክን መምርሕታትን",
                'or': "Seerota Fi Qajeelfama Tirafikaa"
            },
            'VEHICLE': {
                'en': "Vehicle Technical Knowledge",
                'am': "የተሽከርካሪ ቴክኒክ እውቀት",
                'ti': "ፍልጠት ቴክኒክ ተሽከርካሪ",
                'or': "Beekumsa Teeknika Konkolaataa"
            },
            'PRIORITY': {
                'en': "Right of Way & Intersections",
                'am': "የቅድሚያ መብት አጠቃቀም",
                'ti': "ቀዳምነት መሰል ኣጠቓቕማ",
                'or': "Mirga Duraa Fi Walqaxxaamuraa"
            },
            'MARKINGS': {
                'en': "Road Markings",
                'am': "የመንገድ ላይ ምልክቶች (መስመሮች)",
                'ti': "ናይ ፅርግያ ምልክታት (መስመራት)",
                'or': "Mallattoolee Daandii Irraa"
            },
            'SAFETY': {
                'en': "Safety & First Aid",
                'am': "ደህንነት እና የመጀመሪያ እርዳታ",
                'ti': "ድሕንነትን ቀዳማይ ረድኤትን",
                'or': "Nageenya Fi Gargarsa Jalqabaa"
            },
            'PEDESTRIAN': {
                'en': "Pedestrian & Cyclist Safety",
                'am': "የእግረኛና የብስክሌት ደህንነት",
                'ti': "ሓለዋ እግረኛን ብሽክለታን",
                'or': "Nagaa Namoota Miillaa Fi Biskileetii"
            },
            'LEGAL': {
                'en': "Offenses & Penalties",
                'am': "ጥፋቶች እና ቅጣቶች",
                'ti': "ጥሕሰታትን ቅፅዓታትን",
                'or': "Balleessaa Fi Adabbii"
            },
            'GENERAL': {
                'en': "Behavior & General info",
                'am': "በሃሪ እና ጠቅላላ መረጃ",
                'ti': "በሃሪ እና ጠቅላላ መረጃ",
                'or': "Balleessaa Fi Informationni"
            }
        }

        category_objs = {}
        for idx, (code, names) in enumerate(q_categories.items()):
            cat, created = QuestionCategory.objects.get_or_create(
                code=code,
                defaults={'order': idx + 1}
            )
            if created:
                self.stdout.write(f"Created QuestionCategory: {code}")
            else:
                self.stdout.write(f"QuestionCategory {code} already exists")

            category_objs[code] = cat

            for lang, name in names.items():
                QuestionCategoryTranslation.objects.get_or_create(
                    category=cat,
                    language=lang,
                    defaults={
                        'name': name,
                        'description': f"Description for {name}" if lang == 'en' else f"መግለጫ ለ{name}" if lang == 'am' else f"Ibsa {name}"
                    }
                )

        # ===================================================================
        # 2. Road Sign Categories
        # ===================================================================
        rs_categories = {
            'REGULATORY': {
                'en': "Regulatory Signs",
                'am': "ደንበኛ ምልክቶች",
                'ti': "ምልክታት ደንበኛ",
                'or': "Mallattoolee Dhaabbataa"
            },
            'WARNING': {
                'en': "Warning Signs",
                'am': "ማስጠንቀቂያ ምልክቶች",
                'ti': "ምልክታት ማስጠንቀቕያ",
                'or': "Mallattoolee Akeekkachiisaa"
            },
            'INFORMATIVE': {
                'en': "Informative Signs",
                'am': "መረጃ ሰጪ ምልክቶች",
                'ti': "ምልክታት መረጃ ሰጪ",
                'or': "Mallattoolee Odeeffannoo"
            },
        }

        rs_cat_objs = {}
        for idx, (code, names) in enumerate(rs_categories.items()):
            cat, created = RoadSignCategory.objects.get_or_create(
                code=code,
                defaults={'order': idx + 1}
            )
            if created:
                self.stdout.write(f"Created RoadSignCategory: {code}")
            rs_cat_objs[code] = cat

            for lang, name in names.items():
                RoadSignCategoryTranslation.objects.get_or_create(
                    category=cat,
                    language=lang,
                    defaults={'name': name}
                )

        # ===================================================================
        # 3. Road Signs (5 realistic signs)
        # ===================================================================
        road_sign_data = [
            {
                "code": "STOP_001",
                "image": "road_signs/stop.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "Stop", "meaning": "Come to a complete stop", "detailed_explanation": "Drivers must stop completely at the stop line or before entering the intersection."},
                    "am": {"name": "ቆም", "meaning": "ሙሉ በሙሉ ያቁሙ", "detailed_explanation": "አሽከርካሪዎች በማቆሚያ መስመር ላይ ወይም መገናኛው ላይ ከመግባታቸው በፊት ሙሉ በሙሉ መቆም አለባቸው።"},
                    "ti": {"name": "ደው በል", "meaning": "ምሉእ ደው ክብሉ", "detailed_explanation": "ኣካይዳታት ኣብ መስመር ምቁጽጻር ወይ ናብ መገናኒ ከይእተዉ ምሉእ ደው ክብሉ ይግባእ።"},
                    "or": {"name": "Dhaabi", "meaning": "Guutummaan dhaabu", "detailed_explanation": "Hojjettootni mooraa sarara dhaabuu irratti ykn walqunnamtii seenuu dura guutummaan dhaabuu qabu."}
                }
            },
            {
                "code": "YIELD_002",
                "image": "road_signs/yield.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "Yield", "meaning": "Give right of way", "detailed_explanation": "Drivers must slow down and give way to traffic on the intersecting road."},
                    "am": {"name": "መንገድ ስጥ", "meaning": "የመንገድ መብት ስጥ", "detailed_explanation": "አሽከርካሪዎች ፍጥነታቸውን ማለት እና ለመሻገሪያ መንገድ ላይ ለሚገኙ ተሽከርካሪዎች መንገድ ማስተላለፍ አለባቸው።"},
                    "ti": {"name": "መገዲ ሃብ", "meaning": "መሰል መገዲ ሃብ", "detailed_explanation": "ኣካይዳታት ቅልጡፍነቶም ክንክኑ ኣብ ዘጋጥም መገዲ ዘለዉ መካይድታት መገዲ ክህቡ ይግባእ።"},
                    "or": {"name": "Kennee", "meaning": "Karaa kennuu", "detailed_explanation": "Hojjettootni saffisa isaanii hir’isuufi karaa garagaraa irra jiran hojjettootaaf karaa kennuu qabu."}
                }
            },
            {
                "code": "NOENTRY_003",
                "image": "road_signs/no_entry.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "No Entry", "meaning": "Entry prohibited", "detailed_explanation": "Vehicles are not allowed to enter this road or area."},
                    "am": {"name": "መግቢያ የለም", "meaning": "መግቢያ አልባ", "detailed_explanation": "ተሽከርካሪዎች ወደዚህ መንገድ ወይም አካባቢ መግባት አይፈቀድም።"},
                    "ti": {"name": "እታው ኣይተኣትው", "meaning": "እታው ኣይፍቀድ", "detailed_explanation": "መካይድታት ናብዚ መገዲ ወይ ከባቢ ክኣትዉ ኣይፍቀድን።"},
                    "or": {"name": "Seentuun Hin Dandeenye", "meaning": "Seentuun hin eegin", "detailed_explanation": "Makiinaaleen karaa ykn naannoo kana seenuu hin danda'an."}
                }
            },
            {
                "code": "SPEED40_004",
                "image": "road_signs/speed_limit_40.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "Speed Limit 40", "meaning": "Maximum speed 40 km/h", "detailed_explanation": "Do not exceed 40 kilometers per hour in this area."},
                    "am": {"name": "ፍጥነት ገደብ 40", "meaning": "ከፍተኛ ፍጥነት ሰአት 40 ኪ.ሜ.", "detailed_explanation": "በዚህ አካባቢ በሰዓት 40 ኪሎሜትር ከመቶ በላይ አትሽከረክር።"},
                    "ti": {"name": "ልምዲ ቅልጡፍ 40", "meaning": "ዝለዓለ ቅልጡፍ ሰዓት 40 ኪ.ሜ.", "detailed_explanation": "ኣብዚ ከባቢ ካብ 40 ኪሎሜትር በሰዓት ክቕጽል ኣይፍቀድን።"},
                    "or": {"name": "Saffisa Hir'ina 40", "meaning": "Saffisa guddaan sa'aatii 40 km", "detailed_explanation": "Naannoo kana keessatti sa'aatii kilomiitira 40 irra hin ol yaalin."}
                }
            },
            {
                "code": "NOSOUND_005",
                "image": "road_signs/no_horn.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "No Horn", "meaning": "Horn prohibited", "detailed_explanation": "Do not sound your horn in this area, typically near hospitals or schools."},
                    "am": {"name": "ሾጣጣ አይጫወት", "meaning": "ሾጣጣ መጫወት አይፈቀድም", "detailed_explanation": "በዚህ አካባቢ ሾጣጣዎን አትጫወቱ (በተለምዶ በሆስፒታሎች ወይም በትምህርት ቤቶች አቅራቢያ)።"},
                    "ti": {"name": "በትሪ ኣይጭወት", "meaning": "በትሪ ምጭዋት ኣይፍቀድ", "detailed_explanation": "ኣብዚ ከባቢ በትሪኻ ኣይጭወት (መብዛሕትኡ ግዜ ኣብ ወተሃደራት ወይ ቤት ትምህርቲ ኣብ ዚርከብ)።"},
                    "or": {"name": "Bishaan Waa'uu Hin Dandeenye", "meaning": "Faanaa hin waa'in", "detailed_explanation": "Naannoo kana keessatti faanaa keessan hin waa'ina (xiqqoo ispoortaalaa ykn mana barumsaa irra jiru)."}
                }
            },
            {
                "code": "PEDXING_006",
                "image": "road_signs/pedestrian_crossing.png",
                "category": rs_cat_objs['WARNING'],
                "translations": {
                    "en": {"name": "Pedestrian Crossing", "meaning": "Watch for pedestrians", "detailed_explanation": "Pedestrians may be crossing the road. Slow down and be prepared to stop."},
                    "am": {"name": "መንገድ ከማቸው", "meaning": "መንገድ ከማሾችን ተጠንቀቅ", "detailed_explanation": "መንገድ ከማሾች መንገዱን ሊያቋርጡ ይችላሉ። ፍጥነትዎን ይቀንሱ እና ለመቆም ዝግጁ ይሁኑ።"},
                    "ti": {"name": "መጻኢ መንገዲ", "meaning": "ንእግር ተጓዓዝቲ ተጠንቀቕ", "detailed_explanation": "እግር ተጓዓዝቲ መገዲ ክሰግሩ ይኽእሉ እዮም። ቅልጡፍነትኻ ኣንክል ንምቁጽጻር ድማ ተዳለው።"},
                    "or": {"name": "Karaa Darbii Piidoo", "meaning": "Piidoo karaa darban ilaali", "detailed_explanation": "Piidootni karaa darbuu danda'u. Saffisa keessan hir'saa dhaabuuuf qophaa'aa."}
                }
            },
            {
                "code": "SCHOOL_007",
                "image": "road_signs/school_zone.png",
                "category": rs_cat_objs['WARNING'],
                "translations": {
                    "en": {"name": "School Zone", "meaning": "School area ahead", "detailed_explanation": "Drive slowly and carefully. Children may be crossing the road."},
                    "am": {"name": "የትምህርት ቤት ዞን", "meaning": "የትምህርት ቤት አካባቢ ፊት ለፊት", "detailed_explanation": "በዝግታ እና በጥንቃቄ ይግዙ። ልጆች መንገዱን ሊያቋርጡ ይችላሉ።"},
                    "ti": {"name": "ዞን ቤት ትምህርቲ", "meaning": "ከባቢ ቤት ትምህርቲ ኣብ ቅድሚ ገጽ", "detailed_explanation": "ቀስ ኢልካ ብጥንቃቐ ግደ። ህጻናት መገዲ ክሰግሩ ይኽእሉ እዮም።"},
                    "or": {"name": "Naannoo Mana Barumsaa", "meaning": "Mana barumsaa fuuldura", "detailed_explanation": "Saffisaa fi eegginaan hojjedhaa. Ijoolleen karaa darbuu danda'u."}
                }
            },
            {
                "code": "ANIMALS_008",
                "image": "road_signs/animals_crossing.png",
                "category": rs_cat_objs['WARNING'],
                "translations": {
                    "en": {"name": "Animal Crossing", "meaning": "Animals may cross road", "detailed_explanation": "Watch for domestic or wild animals crossing the road, especially in rural areas."},
                    "am": {"name": "እንስሳት መሻገር", "meaning": "እንስሳት መንገድ ሊያቋርጡ ይችላሉ", "detailed_explanation": "ቤተሰብ ወይም ዱር እንስሳት መንገድ ማቋረጫ ተጠንቀቁ (በተለይ በገጠር አካባቢዎች)።"},
                    "ti": {"name": "መስጊር እንስሳ", "meaning": "እንስሳታት መገዲ ክሰግሩ ይኽእሉ", "detailed_explanation": "ንቤት እንስሳታት ወይ እንስሳ በረኻ መገዲ ምስግራ ተጠንቀቕ (መብዛሕትኡ ግዜ ኣብ ገጠራዊ ከባቢ)።"},
                    "or": {"name": "Bineensa Karaa Darbuu", "meaning": "Bineensonni karaa darbuu danda'u", "detailed_explanation": "Mana ykn bineensa bosonaa karaa darban ilaali (addunyaa naannoo baadiyyaa keessatti)."}
                }
            },
            {
                "code": "HAIRPIN_009",
                "image": "road_signs/hairpin_curve.png",
                "category": rs_cat_objs['WARNING'],
                "translations": {
                    "en": {"name": "Hairpin Curve", "meaning": "Sharp double curve ahead", "detailed_explanation": "Extremely sharp curve ahead, usually in mountainous areas. Reduce speed significantly."},
                    "am": {"name": "ጠባይ ጥጥ መዞሪያ", "meaning": "ከፍተኛ ሾጣጣ መዞሪያ ፊት ለፊት", "detailed_explanation": "ከፍተኛ ሾጣጣ መዞሪያ ፊት ለፊት (በተለምዶ በተራራማ አካባቢዎች)። ፍጥነትዎን በከፍተኛ ሁኔታ ይቀንሱ።"},
                    "ti": {"name": "ጸሊም መጠወሪ", "meaning": "በሊሕ ክልተ ክፍሊ መጠወሪ ኣብ ቅድሚ ገጽ", "detailed_explanation": "ኣዝዩ በሊሕ መጠወሪ ኣብ ቅድሚ ገጽ (መብዛሕትኡ ግዜ ኣብ ከባቢ ኣኽራን)። ቅልጡፍነትኻ ብዙሕ ኣንክል።"},
                    "or": {"name": "Qalloo Cimaa", "meaning": "Qalloo cimaa fuuldura", "detailed_explanation": "Qalloo cimaa fuuldura (yeroo baay'ee naannoo gaarreen). Saffisa gadi dhiisaa."}
                }
            },
            {
                "code": "FALLROCK_010",
                "image": "road_signs/falling_rocks.png",
                "category": rs_cat_objs['WARNING'],
                "translations": {
                    "en": {"name": "Falling Rocks", "meaning": "Risk of falling rocks", "detailed_explanation": "Area prone to rockfalls, especially during rainy season or in mountainous regions."},
                    "am": {"name": "የሚወድቁ አልቃሻዎች", "meaning": "የአልቃሻ መውደቅ አደጋ", "detailed_explanation": "አልቃሻዎች ሊወድቁ የሚችሉበት አካባቢ (በተለይ በዝናብ ወቅት ወይም በተራራማ ክልሎች)።"},
                    "ti": {"name": "ዝወድቁ እምኒ", "meaning": "ሓደጋ እምኒ ምውዳቕ", "detailed_explanation": "እምኒ ክወድቁ ዝኽእሉት ከባቢ (መብዛሕትኡ ግዜ ኣብ ወቕቲ ዝናብ ወይ ኣብ ከባቢ ኣኽራን)።"},
                    "or": {"name": "Dhoqqeen Dhiigdu", "meaning": "Dhoqqeen dhiigduu hatattamaa", "detailed_explanation": "Naannoo dhoqqeen dhiigdu (yeroo baay'ee yeroa rooba ykn naannoo gaarreen)."}
                }
            },
            {
                "code": "PARKING_011",
                "image": "road_signs/parking.png",
                "category": rs_cat_objs['INFORMATIVE'],
                "translations": {
                    "en": {"name": "Parking Area", "meaning": "Designated parking zone", "detailed_explanation": "Area where vehicles can be parked legally. Check for time restrictions if any."},
                    "am": {"name": "መኪና ማቆሚያ", "meaning": "የተወሰነ መኪና ማቆሚያ አካባቢ", "detailed_explanation": "ተሽከርካሪዎች በሕጋዊ ሁኔታ ሊቆሙበት የሚችሉበት አካባቢ። ጊዜ ገደቦች ካሉ ያረጋግጡ።"},
                    "ti": {"name": "ከባቢ መቐመጢ መኪና", "meaning": "ተወሰነ ከባቢ መቐመጢ መኪና", "detailed_explanation": "ከባቢ መካይድታት ብሕጋዊ መገዲ ክቐመጡሉ ዝኽእሉት እዩ። እንተኾነ ግዜ ገደባት ኣለዉ ንርአ።"},
                    "or": {"name": "Naannoo Kuufama", "meaning": "Naannoo kuufama murtaa'e", "detailed_explanation": "Naannoo makiinaaleen seeraan kuufamuu danda'an. Yoo ciccimoo yeroon jiraate mirkaneessi."}
                }
            },
            {
                "code": "HOSPITAL_012",
                "image": "road_signs/hospital.png",
                "category": rs_cat_objs['INFORMATIVE'],
                "translations": {
                    "en": {"name": "Hospital Ahead", "meaning": "Hospital in vicinity", "detailed_explanation": "Hospital facility nearby. Drive quietly and be prepared for ambulance traffic."},
                    "am": {"name": "ፊት ለፊት ሆስፒታል", "meaning": "ሆስፒታል አቅራቢያ", "detailed_explanation": "ሆስፒታል በአቅራቢያ አለ። በሰላም ይግዙ እና ለአምቡላንስ ተሽከርካሪ ዝግጁ ይሁኑ።"},
                    "ti": {"name": "ሆስፒታል ኣብ ቅድሚ ገጽ", "meaning": "ሆስፒታል ኣብ ጥቓ", "detailed_explanation": "ሆስፒታል ኣብ ጥቓ ኣሎ። ብህድኣት ግደ ንምንቅስቓስ ኣምቡላንስ ድማ ተዳለው።"},
                    "or": {"name": "Mana Yaalaa Fuuldura", "meaning": "Mana yaalaa dhiyoo", "detailed_explanation": "Mana yaalaa dhiyoo jira. Nagaan hojjedhaa fi makiinaa yaalaaf qophaa'aa."}
                }
            },
            {
                "code": "FUEL_013",
                "image": "road_signs/fuel_station.png",
                "category": rs_cat_objs['INFORMATIVE'],
                "translations": {
                    "en": {"name": "Fuel Station", "meaning": "Gasoline/petrol station ahead", "detailed_explanation": "Fuel filling station available for refueling vehicles."},
                    "am": {"name": "የነዳጅ ጣብያ", "meaning": "የበንዚን/ፔትሮል ጣብያ ፊት ለፊት", "detailed_explanation": "የነዳጅ መሙያ ጣብያ ለተሽከርካሪዎች ነዳጅ ለመሙላት ይገኛል።"},
                    "ti": {"name": "መደበር ነዳጂ", "meaning": "መደበር በንዚን/ፔትሮል ኣብ ቅድሚ ገጽ", "detailed_explanation": "መደበር ምምላእ ነዳጂ ንመካይድታት ነዳጂ ንምምላእ ኣሎ።"},
                    "or": {"name": "Mana Bittaa Naftaa", "meaning": "Mana bittaa naftaa fuuldura", "detailed_explanation": "Mana bittaa naftaa makiinaaleef naftaa guutuu irratti argama."}
                }
            },
            {
                "code": "RESTAREA_014",
                "image": "road_signs/rest_area.png",
                "category": rs_cat_objs['INFORMATIVE'],
                "translations": {
                    "en": {"name": "Rest Area", "meaning": "Place to stop and rest", "detailed_explanation": "Designated area for drivers to take breaks, especially on long journeys."},
                    "am": {"name": "የዕረፍት አካባቢ", "meaning": "ለመቆም እና ለመዝለል ቦታ", "detailed_explanation": "አሽከርካሪዎች ለመዝለል የሚቆሙበት ቦታ (በተለይ በረጅም ጉዞዎች)።"},
                    "ti": {"name": "ከባቢ ዕረፍቲ", "meaning": "ቦታ ንምቁም ንምዕረፍ", "detailed_explanation": "ተወሰነ ቦታ ንኣካይዳታት ንኼዕርፉ (መብዛሕትኡ ግዜ ኣብ ነዊሕ ጕዕዞ)።"},
                    "or": {"name": "Naannoo Boqonnaa", "meaning": "Bakka dhaabuu fi boqonnaa", "detailed_explanation": "Naannoo murtaa'e hojjettootaaf boqonnaa fudhachuuf (yeroo baay'ee imala dheeressa)."}
                }
            },
            {
                "code": "ROUNDABT_015",
                "image": "road_signs/roundabout.png",
                "category": rs_cat_objs['INFORMATIVE'],
                "translations": {
                    "en": {"name": "Roundabout Ahead", "meaning": "Circular intersection ahead", "detailed_explanation": "Prepare to enter a circular intersection. Give way to vehicles already in the roundabout."},
                    "am": {"name": "ዙር ክብ መገናኛ", "meaning": "ክብ መገናኛ ፊት ለፊት", "detailed_explanation": "ለክብ መገናኛ መግባት ይዘጋጁ። በዙር ክብ መገናኛው ውስጥ ለሚገኙ ተሽከርካሪዎች መንገድ ስጡ።"},
                    "ti": {"name": "ዙር ክብ መገናኒ ኣብ ቅድሚ ገጽ", "meaning": "ክብ መገናኒ ኣብ ቅድሚ ገጽ", "detailed_explanation": "ንክብ መገናኒ ንኽትኣትዉ ተዳለዉ። ንመካይድታት ኣብቲ ዙር ክብ መገናኒ ዘለዉ መገዲ ሃቡ።"},
                    "or": {"name": "Walqunnamtii Geengoo Fuuldura", "meaning": "Walqunnamtii geengoo fuuldura", "detailed_explanation": "Walqunnamtii geengoo seenuur qophaa'aa. Makiinaaleen walqunnamtii geengoo keessa jiran kennuu."}
                }
            }
        ]

        sign_objs = []
        for sign in road_sign_data:
            obj, created = RoadSign.objects.get_or_create(
                code=sign["code"],
                defaults={'image': sign["image"], 'category': sign["category"]}
            )
            if created:
                self.stdout.write(f"Created RoadSign: {sign['code']}")
            sign_objs.append(obj)

            for lang in ['en', 'am', 'ti', 'or']:
                RoadSignTranslation.objects.get_or_create(
                    road_sign=obj,
                    language=lang,
                    defaults=sign["translations"][lang]
                )

        # ===================================================================
        # 4. Payment Methods
        # ===================================================================
        payment_methods = [
            {"code": "BOA", "name": "Bank of Abyssinia", "type": "BANK_TRANSFER", "order": 1},
            {"code": "TELEBIRR", "name": "Telebirr", "type": "MOBILE_WALLET", "order": 2},
            {"code": "DASHEN", "name": "Dashen Bank", "type": "BANK_TRANSFER", "order": 3},
        ]

        for pm in payment_methods:
            obj, created = PaymentMethod.objects.get_or_create(
                code=pm["code"],
                defaults={
                    'name': pm["name"],
                    'method_type': pm["type"],
                    'is_active': True,
                    'order': pm["order"]
                }
            )
            if created:
                self.stdout.write(f"Created PaymentMethod: {pm['code']}")

            translations = {
                "en": {"account_details": "Account: 1000123456789", "instruction": "Transfer the amount and send reference number."},
                "am": {"account_details": "አካውንት፡ 1000123456789", "instruction": "ገንዘቡን ይላኩ እና ማጣቀሻ ቁጥር ይላኩ።"},
                "ti": {"account_details": "ኣካውንቲ፡ 1000123456789", "instruction": "ገንዘብ ልኣኽ እና ቁጽሪ ማጣቀሻ ልኣኽ።"},
                "or": {"account_details": "Akaawuntii: 1000123456789", "instruction": "Maallaqa erguu fi lakkoofsa maqaqsa erguu."},
            }
            for lang, data in translations.items():
                PaymentMethodTranslation.objects.get_or_create(
                    payment_method=obj,
                    language=lang,
                    defaults=data
                )

        # ===================================================================
        # 5. Subscription Tiers (no 'name' field — only translations)
        # ===================================================================
        tiers = [
            {"price": 0, "days": 10, "max_exams": 1, "full_quiz": False, "is_free": True, "order": 0,
             "en": "Free Plan", "am": "ነጻ ፓኬጅ", "ti": "ፕላን ብዝክፈለ", "or": "Paakeejii Bilisaa"},
            {"price": 100, "days": 30, "max_exams": 5, "full_quiz": True, "is_free": False, "order": 1,
             "en": "Basic Monthly", "am": "መሰረታዊ ወርሃዊ", "ti": "መባእታ ወርሒ", "or": "Ji'a Bu'uuraa"},
            {"price": 250, "days": 90, "max_exams": 15, "full_quiz": True, "is_free": False, "order": 2,
             "en": "Premium 3-Month", "am": "ፕሪሚየም 3-ወር", "ti": "ፕሪሚየም 3 ወርሒ", "or": "Ol'aanaa 3 Ji'a"},
        ]

        tier_objs = []
        for t in tiers:
            tier, created = SubscriptionTier.objects.get_or_create(
                price=t["price"],
                duration_days=t["days"],
                defaults={
                    'max_exam_number': t["max_exams"],
                    'full_road_sign_quiz': t["full_quiz"],
                    'ai_assistance_enabled': t["days"] > 30,
                    'personalized_feedback_enabled': t["days"] > 30,
                }
            )
            if created:
                self.stdout.write(f"Created SubscriptionTier: {t['en']}")
            tier_objs.append(tier)

            for lang in ['en', 'am', 'ti', 'or']:
                SubscriptionTierTranslation.objects.get_or_create(
                    tier=tier,
                    language=lang,
                    defaults={'name': t[lang], 'description': f"{t[lang]} subscription plan"}
                )


        questions = [
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "አልኮል ጠጥቶ ማሽከርከር ውሳኔን ያሳጣል?",
                            "en": "Does drinking alcohol impair decision-making?",
                            "ti": "ኣልኮል ስሪሕካ ምንዳድ ንውሳኔ የሚጎድሎ?",
                            "or": "Dhandhamni al-koolii dhuguu murteen murteessuu dhabamsiisaa?",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "Incorrect option A",
                                    "ti": "ስሕተት ምርጫ ሀ",
                                    "or": "Dogoggora filannoo A",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "አብዛኛውን ጊዜ አልኮል መጠጥ ጠጥተው የሚያሽከረክሩ አደጋ አይደርስባቸውም",
                            "en": "Most of the time, people who drink alcohol and drive do not get into accidents.",
                            "ti": "ኣብ መብዛሕትኡ ግዜ፡ ኣልኮል ስሪሖም ዝደይቡ ሰባት ኣደጋ ኣይከሳዕዎምን እዮም።",
                            "or": "Yeroo baay'eedhaan, namoonni dhandhamni al-koolii dhuganii dhaqanii balaan isaaniif hin dhufu.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "90 ፐርሰንት የሚሆነው መረጃ የሚሰበሰበው በማየት ነው",
                            "en": "90 percent of information is gathered through sight.",
                            "ti": "90 ሚእታዊት መረጃ ብምርኣይ እዩ ዝእክብ።",
                            "or": "Piroseentii 90% oduu argamu argachuun ijaan ta'a.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ማስተዋል ማለት ምን ማለት ነው",
                            "en": "What does perception mean?",
                            "ti": "ምምዕዓል እንታይ ማለት እዩ?",
                            "or": "Meeqaatni jechuun maal jechuu dha?",
                            "choices": [
                                {
                                    "am": "መረጃ ማቀናበር",
                                    "en": "Processing information",
                                    "ti": "መረጃ ምድላው",
                                    "or": "Oduu dammachiisuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "መረጃን መሰብሰብ",
                                    "en": "Gathering information",
                                    "ti": "መረጃ ምእካብ",
                                    "or": "Oduu walitti qabuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መረጃን ወደ ኦዕምሮ መላክ",
                                    "en": "Sending information to the brain",
                                    "ti": "መረጃ ናብ ሓንጎ ምልኣኽ",
                                    "or": "Oduu gara sammuutti geessuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "መነቃቃት ወይም መነሳሳት የ _____ ባህሪ ነው",
                            "en": "Being alert or stimulated is the behavior of _____.",
                            "ti": "ምልዕዓል ወይ ምንቃዕ ናይ _____ ባህሪ እዩ።",
                            "or": "Qajelummaan yookiin daddarsiisuu _____ amala ta'a.",
                            "choices": [
                                {
                                    "am": "የእንስሳት",
                                    "en": "Animals",
                                    "ti": "እንስሳታት",
                                    "or": "Bineensota",
                                    "is_correct": True
                                },
                                {
                                    "am": "መረጃን መሰብሰብ",
                                    "en": "Gathering information",
                                    "ti": "መረጃ ምእካብ",
                                    "or": "Oduu walitti qabuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "የሰው",
                                    "en": "Humans",
                                    "ti": "ሰብ",
                                    "or": "Nama",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "መንገዱ ዝናባማና ጭጋጋማ የአየር ሁኔታ ይበዛበታል ሲባል ምን እየገለጽን ነው?",
                            "en": "What are we describing when we say the road is hilly, winding, and often has bad weather?",
                            "ti": "መንገዲ ኣኽራንን መዘውዒን ዝኾነ ከምኡ’ውን ኩነታት ኣየር እናጸንሐ ምስበልና እንታይ ኢና እንገልጽ?",
                            "or": "Yoo karaa gaaraa, qallaawoofi haala qilleensaa hammaataa qabu jedhanii dubbannu, maal ibsaa jirra?",
                            "choices": [
                                {
                                    "am": "አከባቢያዊ ሁኔታ",
                                    "en": "Local conditions",
                                    "ti": "ናይ ከባቢ ኩነታት",
                                    "or": "Haala naannoo",
                                    "is_correct": True
                                },
                                {
                                    "am": "የመንገድ መልካምድራዊ ሁኔታ",
                                    "en": "Road geometric condition",
                                    "ti": "ናይ መንገዲ ጂኦሜትራዊ ኩነታት",
                                    "or": "Haala ji'oomitirii karaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የመንገድ ደረጃና አይነት",
                                    "en": "Road grade and type",
                                    "ti": "ደረጃን ዓይነትን መንገዲ",
                                    "or": "Sadarkaafi gosa karaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ጉዞ ከመጀመሩ በፊት አንድ አሽከረካሪ ጥሩ መንገድ መምረጥ ይኖርበታል።",
                            "en": "A driver must choose a good route before starting the journey.",
                            "ti": "ሓደ ሻፈር ቅድሚ ጉዕዞ ምጅማሩ ጽቡቕ መንገዲ ክመርጽ ኣለዎ።",
                            "or": "Konkolaataa seenaa sirrii filachuun dirqama yoo seenaa eegaluu dura.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "የሞገደኛ አሽከርካሪ ባህሪ ያልሆነው የቱ ነው?",
                            "en": "Which one is NOT the behavior of an aggressive driver?",
                            "ti": "ኣብቲ ናይ ሞገደኛ ሻፈር ባህሪ ዘይንጡፍ እንታይ እዩ?",
                            "or": "Amala konkolaataa jeeqaa ta'een kan hin taane kami?",
                            "choices": [
                                {
                                    "am": "ሕግ ማክበር",
                                    "en": "Obeying the law",
                                    "ti": "ሕጊ ምኽባር",
                                    "or": "Seera kabajuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ጠጥቶ አለምሽከርከር",
                                    "en": "Driving under the influence of alcohol",
                                    "ti": "ስሪሕካ ምንዳድ",
                                    "or": "Dhandhamni al-koolii dhuganii dhaqaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "በቂ እረፍት በማድረግ ምሽከርከር",
                                    "en": "Driving without adequate rest",
                                    "ti": "እኹል ዕረፍቲ ምቕራብ ዘይብሉ ምንዳድ",
                                    "or": "Boqonnaa ga'aa hin qabneen dhaqaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "የአሽከርካሪዎች አላስፈላጊ ባህሪያት የሆኑትን ለዩ",
                            "en": "Identify the unnecessary behaviors of drivers.",
                            "ti": "ናይ ሻፈራት ዘየድልዩ ባህርያት መለልዩ።",
                            "or": "Amaloota konkolaattootaa kan hin barbaachisne mul'isi.",
                            "choices": [
                                {
                                    "am": "ሞገደኝነት",
                                    "en": "Aggressiveness",
                                    "ti": "ሞገደኝነት",
                                    "or": "Jeequmsi",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሱሰኝነት",
                                    "en": "Negligence",
                                    "ti": "ሱሰኝነት",
                                    "or": "Dandeettii dhiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ቸልተኝነት",
                                    "en": "Carelessness",
                                    "ti": "ቸልተኝነት",
                                    "or": "Of-qabatamummaan",
                                    "is_correct": False
                                },
                                {
                                    "am": "ኃላፊነት መዘንጋት",
                                    "en": "Avoiding responsibility",
                                    "ti": "ሓላፍነት ምሕዳር",
                                    "or": "Hundeeffannoo baasuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ አልተሰጠም",
                                    "en": "No answer",
                                    "ti": "መልሲ ኣይተሃበን",
                                    "or": "Deebii hin kenname",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ከሚከተሉት ውስጥ ሞገደኛ አሽከራክሪ አነዳድ የሚገልጽ የቱ ነው?",
                            "en": "Which of the following best describes an aggressive driver?",
                            "ti": "ካብዚ ዝስዕብ እዚ ሞገደኛ ሻፈር ዝገልጽ እንታይ እዩ?",
                            "or": "Kana irraa kamtu konkolaataa jeeqaa ta'ee ibsuu irratti caala?",
                            "choices": [
                                {
                                    "am": "በተደጋጋሚ በተረበሸና በመጥፎ ስሜት ማሽከርከር",
                                    "en": "Driving frequently in a bad and angry mood",
                                    "ti": "ብተደጋጋሚ ብመጥፎ ስሜትን ቁጥዐን ምንዳድ",
                                    "or": "Yeroo baay'ee hammeenyaafi dallansaa qabuun dhaqaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "በአላስፈላጊ ባህሪ ውስጥ ሆኖ የማሽከርከር ውጤት ነው",
                                    "en": "It is the result of driving with unnecessary behavior",
                                    "ti": "ናይ ዘየድልዩ ባህሪ ውጽኢት እዩ",
                                    "or": "Booda amala hin barbaachisneen dhaquu irraa kan argamuudha",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናችው",
                                    "en": "Answers 1 and 2",
                                    "ti": "1 ከ 2 መልስታት እዮም",
                                    "or": "Deebii 1 fi 2",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ጎማ ከተሽካሚ ክፍል ይመደባል።",
                            "en": "A tire is classified as a suspension part.",
                            "ti": "ጎማ ከተሽካሚ ክፍል ይግበር።",
                            "or": "Kophaa dhaabbataa (suspension) irratti tajaajila godhatu.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "የተሽከርካሪ ጎማ መንሸራተት ከጀመረ ፍትነት መቀነስ ይኖርብናል።",
                            "en": "If a vehicle's tire starts to skid, we must reduce speed.",
                            "ti": "ጎማ ማንቀሳቐስ ምስጅምር ምንዳድ ክንነክስ ኣሎና።",
                            "or": "Yoo kophiin konkolaataa dhidhimuu eegale, saffisaa hir'isuu qabna.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ተሽከርካሪ ስናቆም ጎማን ከመንገዱ Yእርዝ አስጠግቶ ማቆም ያለብን ርቀት ስንት ነው?",
                            "en": "When stopping a vehicle, what distance should we keep the tire from the edge of the road?",
                            "ti": "ማንካስ ምስናቆም ጎማ ካብ ወገን መንገዲ ክንርሒዮ ዘሎና ውሑድ እዩ?",
                            "or": "Yoo konkolaataa dhaabbannu, karaa irraa meecheen fageenya kamiin fagaattu qabna?",
                            "choices": [
                                {
                                    "am": "40 ሳ.ሜ",
                                    "en": "40 cm",
                                    "ti": "40 ሳ.ሜ",
                                    "or": "40 cm",
                                    "is_correct": True
                                },
                                {
                                    "am": "30 ሳ.ሜ",
                                    "en": "30 cm",
                                    "ti": "30 ሳ.ሜ",
                                    "or": "30 cm",
                                    "is_correct": False
                                },
                                {
                                    "am": "60 ሳ.ሜ",
                                    "en": "60 cm",
                                    "ti": "60 ሳ.ሜ",
                                    "or": "60 cm",
                                    "is_correct": False
                                },
                                {
                                    "am": "100 ሳ.ሜ",
                                    "en": "100 cm",
                                    "ti": "100 ሳ.ሜ",
                                    "or": "100 cm",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ተሽከርካሪ ስለመቅደም ትክክል የሆነው የቱ ነው?",
                            "en": "Regarding overtaking, which one is correct?",
                            "ti": "ዛዚ ምቕዳም ብዛዕባ እቲ ልክዕ እንታይ እዩ?",
                            "or": "Waan darbuuf, kamtu sirriidha?",
                            "choices": [
                                {
                                    "am": "ለመቅደም በግራ በኩል መሆኑን መገንዘብ",
                                    "en": "Understanding that overtaking is from the left side",
                                    "ti": "ምቕዳም ካብ ጸጋማይ ሸነኽ ምዃኑ ምግንዛብ",
                                    "or": "Darbuun biddeen mirgaa irraa akka ta'e hubachuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሦስተኛ ተደራቢ ሆኖ መቅደም ክልክል እንደሆነ ማስተዋል",
                                    "en": "Recognizing that overtaking as a third party is prohibited",
                                    "ti": "ሳልሳይ ኣካል ኰነ ምቕዳም ከም ዘይፍቀድ ምግንዛብ",
                                    "or": "Haalli sadaffaa ta'ee darbuun dhorgamaa akka ta'e hubachuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ለመቅደም የተከለከለ ስፍራ እንዳልሆነ ማየት",
                                    "en": "Seeing that the place is not prohibited for overtaking",
                                    "ti": "ምቕዳም ዘይፍቀድ ቦታ ከም ዘይኮነ ምርኣይ",
                                    "or": "Bakka darbuu hin fedhamne akka hin jirreetti arguu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም መልስ ነው",
                                    "en": "All are answers",
                                    "ti": "ኩሎም መልሲ እዮም",
                                    "or": "Hundinuu deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "በሀገራችን ሕግ ተሽከርካሪን መክደም የሚቻለው በየትኛው በኩል ነው?",
                            "en": "According to the law in our country, from which side can a vehicle be overtaken?",
                            "ti": "ብሕጊ ሃገርና ተሽከርካሪ ካበይ ሸነኽ ክድርብ ይከኣል?",
                            "or": "Seera biyya keenyaatiin, konkolaataa bakka kam irraa darbuu danda'ama?",
                            "choices": [
                                {
                                    "am": "በቀኝ",
                                    "en": "Right side",
                                    "ti": "የምሕረት ሸነኽ",
                                    "or": "Irrna mirgaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "በመሀል",
                                    "en": "Middle",
                                    "ti": "መንካ",
                                    "or": "Gidduu",
                                    "is_correct": False
                                },
                                {
                                    "am": "በግራ",
                                    "en": "Left side",
                                    "ti": "ጸጋማይ ሸነኽ",
                                    "or": "Irrna bitaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ለመንገድ የተሰጠውን የፍጥነት ወሰን ገደብ ማክበር ግዴታ አደለም።",
                            "en": "It is not mandatory to obey the speed limit given for the road.",
                            "ti": "ንመንገዲ ዝተሃበ ዶሮ ፍጥነት ምኽባር ግዴታ ኣይኮነን።",
                            "or": "Saffisa karaa irratti murteeffame kabajuu dirqama hin taane.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ተሽከረካሪ መቅደም ቢያስፈልግ መቅደም የሚቻለው በቅኝ በኩል መሆኑን አሽከርካሪው ሊገነዘብ ይገባል።",
                            "en": "If a driver needs to overtake, the driver must understand that overtaking is done from the left side.",
                            "ti": "ሻፈር ምቕዳም እንተደልዩ ካብ ጸጋማይ ሸነኽ ከም ዝግበር ክግንዘብ ኣለዎ።",
                            "or": "Yoo konkolaataa darbuu barbaadu, darbuun biddeen mirgaa irraa akka ta'e hubachuu qaba.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "በተጨናነቀ መንገድ ከፊት ለፊት የሚመጣ ተሽከርካሪ ጋር ለመተላለፍ መደረግ ያለበት",
                            "en": "What should be done to pass an oncoming vehicle on a narrow road?",
                            "ti": "ኣብ ጸቢብ መንገዲ ካብ ቅድሚት ዝመጽእ ተሽከርካሪ ምስ ንሓሊፍ እንታይ ክንገብር ኣሎ?",
                            "or": "Karaan dhiphoo keessa konkolaataa fuulduraa irraa dhufu qunnamuu danda'u, maal godhuu qaba?",
                            "choices": [
                                {
                                    "am": "ቆሞ ማሳለፍ",
                                    "en": "Stop and let it pass",
                                    "ti": "ደው ኢሉ ምሕላፍ",
                                    "or": "Dhaabbachuun dhiisuuf dhiisuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "የመንገድ ቀኝ ይዞ ማሽከረከር",
                                    "en": "Drive while keeping to the right side of the road",
                                    "ti": "ናይ መንገዲ የምሕረት ሸነኽ ሒዙ ምንዳድ",
                                    "or": "Karaa irra dhaabbachuun gara bitaatiin dhaquu",
                                    "is_correct": False
                                },
                                {
                                    "am": "እንደትራፊኩ ሁኔታ ፍጥነት መቀነስ",
                                    "en": "Reduce speed according to the traffic situation",
                                    "ti": "ብመሰረት ኩነታት ትራፊክ ፍጥነት ምንካስ",
                                    "or": "Haala traafikii irratti hundaa'uun saffisaa hir'isuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ለባጃጅ፣ ሞተር ሳይክልና አውቶሞቢል በከተማ ክልል የተፈቀደ ከፍተኛ የፍጥነት ወሰን",
                            "en": "The maximum permitted speed limit for Bajaj, motorcycle, and automobile in the city area.",
                            "ti": "ኣብ ከተማ ኣከባቢ ንባጃጅ፣ ሞተር ሳይክልን መኪና ዝፍቀድ ወሰን ፍጥነት",
                            "or": "Ganda keessatti Bajaj, mootorsaayikilii fi mootorbootii irratti saffisa maksimamii kan eeyyamamu.",
                            "choices": [
                                {
                                    "am": "100",
                                    "en": "100",
                                    "ti": "100",
                                    "or": "100",
                                    "is_correct": True
                                },
                                {
                                    "am": "70",
                                    "en": "70",
                                    "ti": "70",
                                    "or": "70",
                                    "is_correct": False
                                },
                                {
                                    "am": "80",
                                    "en": "80",
                                    "ti": "80",
                                    "or": "80",
                                    "is_correct": False
                                },
                                {
                                    "am": "60",
                                    "en": "60",
                                    "ti": "60",
                                    "or": "60",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "በጉዞ ላይ ከመቆማችህን በፊት አስቅቀድመን አግራ ፍሬቻ ማሳየት አለብን",
                            "en": "Before stopping during a trip, we must show the left indicator in advance.",
                            "ti": "ቅድሚ ምዕረፍና ኣብ ጉዕዞ ናብ ጸጋማይ ፍሬቻ ኣቐዲምና ክንርእዮ ኣሎና።",
                            "or": "Yoo deemaa deemaa dhaabbannu, dura ifaa gara bitaatiin agarsiisuu qabna.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "የሰሌዳ መብራት በምሽት ጊዜ ከኋላ በኩል ያለውን ቦታ አጥርቶ ለማየት ያገለግላል።",
                            "en": "Dashboard lights are used to illuminate and see the area behind during night time.",
                            "ti": "ናይ ዳሽቦርድ መብራት ኣብ ምሸት ናይ ድሕሪት ቦታ ንምብራህን ንምርኣይን የገልግል።",
                            "or": "Ifaan daashboordii, halkan yeroo dhaabbatan bakka duubaa ibsuuf ni tajaajila.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "የተሽከርካሪ ሰሌዳ አብዛኛውን ጊዜ ከተሽከራካሪ ፊት ለፍቲ ብቻ ይገኛል።",
                            "en": "A vehicle's dashboard is usually only found in front of the driver.",
                            "ti": "ናይ ተሽከርካሪ ዳሽቦርድ መብዛሕትኡ ግዜ ኣብ ቅድሚት ሻፈር ጥራይ እዩ ዝርከብ።",
                            "or": "Daashboordiin konkolaataa, yeroo baay'ee fuula konkolaataa qofatti argama.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ፍሬቻ ከፊትና ከኋላ ብቻ የሚገኝ የመብራት አይነት ነው።",
                            "en": "Indicators are a type of light found only in the front and rear.",
                            "ti": "ፍሬቻ ኣብ ቅድሚትን ድሕሪትን ጥራይ ዝርከብ ዓይነት መብራት እዩ።",
                            "or": "Ifaan mallattoo ta'an, fuula fi duubaa qofatti argamu.",
                            "choices": [
                                {
                                    "am": "እውነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "አንድ ተሽከረካሪ ከቆመበት ለመነሳት ቢፈልግ የሚጠቀመው ፍሬቻ የቱ ነው",
                            "en": "When a vehicle wants to move from a stopped position, which indicator does it use?",
                            "ti": "ሓደ ተሽከርካሪ ካብ እተዓቅመሉ ንምንቅስቓስ ክጥቀመሉ ዘለዎ ፍሬቻ እንታይ እዩ?",
                            "or": "Yoo konkolaataa dhaabbatee irraa deebi'uu barbaade, ifaa kamiin itti agarsiisa?",
                            "choices": [
                                {
                                    "am": "የቀኝ",
                                    "en": "Right indicator",
                                    "ti": "የምሕረት ፍሬቻ",
                                    "or": "Ifaa gara mirgaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሃዛርድ",
                                    "en": "Hazard lights",
                                    "ti": "ሓደጋ መብራት",
                                    "or": "Ifaan bala'aa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የግራ",
                                    "en": "Left indicator",
                                    "ti": "ጸጋማይ ፍሬቻ",
                                    "or": "Ifaa gara bitaati",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ከሚከተሉት አንዱ በዳሽቦርድ ላይ አይገኝም",
                            "en": "Which one of the following is not found on the dashboard?",
                            "ti": "ካብዚ ዝስዕብ እዚ ኣብ ዳሽቦርድ ዘይትርከብ እንታይ እዩ?",
                            "or": "Kana irraa kamtu daashboordii irratti hin argamu?",
                            "choices": [
                                {
                                    "am": "የነዳጅ ጌጅ",
                                    "en": "Fuel gauge",
                                    "ti": "ናይ ነዳጅ ጌጅ",
                                    "or": "Madaalliibaa qorichaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "የሞተር ዘይት ግፊት ጌጅ",
                                    "en": "Engine oil pressure gauge",
                                    "ti": "ናይ ዘይት ግፊት ጌጅ",
                                    "or": "Madaalliibaa ciminaa zayita mashiinaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የሞተር ሙቀት ጌጅ",
                                    "en": "Engine temperature gauge",
                                    "ti": "ናይ ሙቀት ጌጅ",
                                    "or": "Madaalliibaa ho'a mashiinaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ አልተሰጠም",
                                    "en": "No answer",
                                    "ti": "መልሲ ኣይተሃበን",
                                    "or": "Deebii hin kenname",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "በመኪና ዉስጥ ክሹፌሩ ፊት ለፊት ያሉት የመቆጣጠሪያ መሳሪያዎች የተሽከርካሪዉን የአገልግሎት ዓይነት ለማወቅ ያገለግላሉ፡፡",
                            "en": "The control instruments in front of the driver inside the car help identify the type of vehicle service.",
                            "ti": "ኣብ ውሽጢ መኪና ኣብ ቅድሚት ሻፈር ዘሎ መሳርያታት ኮንትሮል ነቲ ተሽከርካሪ ዓይነት ኣገልግሎት ንምፍላጥ ይገልጽ።",
                            "or": "Qorannoon waliigalaa waliin konkolaataa gidduutti argaman, gosa tajaajilaa konkolaataa ibsuuf gargaaru.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ሞተር በሚኒሞ ማሰራት ለምን አስፈለገ?",
                            "en": "Why is it necessary to run the engine at idle?",
                            "ti": "ሞተር በሚኒሞ ምምሕራሽ ንምንታይ ኣስፍላጢ እዩ?",
                            "or": "Maaliif mashiinni idilii ta'ee sochuu qaba?",
                            "choices": [
                                {
                                    "am": "ሞተር ለማሞት",
                                    "en": "To warm up the engine",
                                    "ti": "ሞተር ንምውዳድ",
                                    "or": "Mashiinaa ho'isuuf",
                                    "is_correct": True
                                },
                                {
                                    "am": "ዘይት ወደ ሁሉም ቦታ እስኪደርስ(አንዲሰራጭ)",
                                    "en": "For oil to reach all parts (to circulate)",
                                    "ti": "ዘይት ናብ ኩሉ ቦታ ክበጽሕ (ንምስራጭ)",
                                    "or": "Zayitaanni bakka hunda ga'uuf (faayinaa godhuuf)",
                                    "is_correct": False
                                },
                                {
                                    "am": "የራዲያተር ዉሃ እስኪሞቅ",
                                    "en": "For radiator water to heat up",
                                    "ti": "ማይ ራዲያተር ክውድድ",
                                    "or": "Bishaan raadiyeetaraa ho'uuf",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በስራ ላይ የነበረ የተሽከርካሪ ሞተር ለማጥፋት ማድረግ ያለብን",
                            "en": "What should we do to turn off a vehicle engine that was running?",
                            "ti": "እተንቀሳቀሰ ዝነበረ ሞተር ተሽከርካሪ ንምጥፋእ እንታይ ክንገብር ኣሎ?",
                            "or": "Mashiinaa socho'aa ture maal godhuu qabnaa?",
                            "choices": [
                                {
                                    "am": "በሚኒሞ ማሰራት",
                                    "en": "Run at idle",
                                    "ti": "በሚኒሞ ምምሕራሽ",
                                    "or": "Idilii ta'ee sochisuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ቀዝቃዛ አየር አካባቢ አቁሞ ማቀዝቀዝ",
                                    "en": "Stop and cool in a cool air environment",
                                    "ti": "ኣብ ዝሑል ኣየር ኣካባቢ ደው ኢሉ ምቝምሻእ",
                                    "or": "Bakka qilleensa qabbanaa keessatti dhaabbachuun qabachuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ወዲያዉኑ ሞተር አለማጥፋት",
                                    "en": "Do not turn off the engine immediately",
                                    "ti": "ብቕጽበት ሞተር ኣይጥፍእን",
                                    "or": "Mashiinaa dhiqaatitti hin cufin",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ተሽከርካሪ በምናንቀሳቅስበት ጊዜ ማድረግ የሚገባን የቱ ነዉ",
                            "en": "What should we do when moving a vehicle?",
                            "ti": "ተሽከርካሪ ምስንቀሳቕስ እንታይ ክንገብር ኣሎ?",
                            "or": "Yoo konkolaataa sochoosinu, maal godhuu qabna?",
                            "choices": [
                                {
                                    "am": "አካባቢን በመቃኘት ቅድሚያ ለሚያገኙ ቅድሚያ መስጠት",
                                    "en": "Check surroundings and give priority to those who have priority",
                                    "ti": "ከባቢ ብምቕናሽ ንቀዳምነት ዘለዎም ቅድሚያ ምሃብ",
                                    "or": "Naannoo qorachuufi namoota duraan darban dhiisuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ፍሪሲዮን በመርገጥ አንደኛ ማርሽ ማስገባት",
                                    "en": "Press clutch and engage first gear",
                                    "ti": "ፍሪሽን ብምጭብባጥ ቀዳማይ ማርሽ ምእታው",
                                    "or": "Killee cabsuu fi geerii tokkoffaa seensuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ለመነሳት የቀኝ ፍሬቻ መጠቀም",
                                    "en": "Use right indicator to start",
                                    "ti": "ንምንቅስቓስ የምሕረት ፍሬቻ ምጥቃም",
                                    "or": "Deebi'uuf ifaa gara mirgaatiin agarsiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Answers 1 and 2",
                                    "ti": "1 ከ 2 መልስታት እዮም",
                                    "or": "Deebii 1 fi 2",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ጉዞ ከመጀመር በፊት የሚደረግ የተሽከርካሪ ፍተሻ ዉስጥ የሚካተተዉ የቴ ነዉ",
                            "en": "Which of these is included in the vehicle inspection before a journey?",
                            "ti": "ኣብ ቅድሚ ጉዕዞ እተገብር ፍተሻ ተሽከርካሪ ውሽጢ ዝካተተ እንታይ እዩ?",
                            "or": "Kana irraa kamtu qorannoo konkolaataa eegaluu dura keessatti hammata?",
                            "choices": [
                                {
                                    "am": "ዘይት",
                                    "en": "Oil",
                                    "ti": "ዘይት",
                                    "or": "Zayitaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ነዳጅ",
                                    "en": "Fuel",
                                    "ti": "ነዳጅ",
                                    "or": "Qorichaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ጎማ",
                                    "en": "Tire",
                                    "ti": "ጎማ",
                                    "or": "Kophaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የሞተር መሰረታዊ ክፍሎች በ4 ይከፈላሉ።",
                            "en": "Basic engine parts are divided into 4.",
                            "ti": "ኣእምሮ ሞተር ክፋልታት ብ4 ይከፈላሉ።",
                            "or": "Qaamolee bu'uuraa mashiinaa afuritti qoodamu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "የራዲያተር ዉሃ ቢቆሽሽ ሞተር ሰርቪስ ማድረግ ያስፈልጋል፡፡",
                            "en": "If radiator water runs out, the engine needs servicing.",
                            "ti": "ማይ ራዲያተር እንተቆሸሸ ሞተር ኣገልግሎት ከም ዘድሊ እዩ።",
                            "or": "Yoo bishaan raadiyeetaraa dhumee, mashiinaan tajaajilaa barbaacha.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ሞተር ከልክ በላይ ሲሞቅ ምን መደረግ አለበት?",
                            "en": "What should be done when the engine overheats?",
                            "ti": "ሞተር ካብ ዓቐኑ ንላዕሊ ምስውድድ እንታይ ክግበር ኣለዎ?",
                            "or": "Yoo mashiinaan ho'ina isaa dabre, maal godhuu qaba?",
                            "choices": [
                                {
                                    "am": "በሚኒሞ ማሰራት",
                                    "en": "Run at idle",
                                    "ti": "በሚኒሞ ምምሕራሽ",
                                    "or": "Idilii ta'ee sochisuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "አቁሞ በአካባቢዉ አየር እንዲቀዘቅዝ ማድረግ",
                                    "en": "Stop and let it cool in the ambient air",
                                    "ti": "ደው ኢሉ ኣብቲ ኣካባቢ ኣየር ክቅዝን ምግባር",
                                    "or": "Dhaabbachuun qilleensa naannoo keessatti qabachuuf dhiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Answers 1 and 2",
                                    "ti": "1 ከ 2 መልስታት እዮም",
                                    "or": "Deebii 1 fi 2",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ሞተር በፍላይ ዊል እና ሞተሪኖ አማካኝነት ይነሳል፡፡",
                            "en": "The engine starts through the flywheel and motorino.",
                            "ti": "ሞተር በፍላይ ዊልን ሞተሪኖን ብዕማም ይንስኣል።",
                            "or": "Mashiinni flywheel fi motorinoon jalqaba.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "የእግረኛ ምስል ያለበት አረንጓዴ የትራፊክ መብራት ሲበራ እግረኞች በዜብራ ላይ ፈጠን ብሰዉ መንገድ እንዲሻገሩ ይፈቅዳል፡፡",
                            "en": "When a green traffic light with a pedestrian symbol is on, it allows pedestrians to cross quickly on the zebra crossing.",
                            "ti": "ምስሊ እግረኛ ዘለዎ ኣረንጓዴ ትራፊክ መብራት ምስበራ እግረኛታት ኣብ ዜብራ ቅልጡፍ ክሓልፉ ይፍቀድ።",
                            "or": "Yoo ifaa traafikii magariisaan mallattoo piyootaatiin qabamu ibsaa, namoota piyootaan deemantu zebraa irratti ariifatanii darbuu danda'u.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የተሽከርካሪ የትራፊክ ማስተላለፊያ መብራት በማሽከርከር ላሉ አሽከርካሪዎች ብቻ መልዕክት የሚያስተላልፍ ሲሆን አሽከርካሪዎች በጥንቃቄ መንገድ እንዲያቋርጡና ከሌሎች አሽከርካሪዎች ጋር በቀላሉ መተላለፍ እንዲችሉ ያግዛል፡፡",
                            "en": "Vehicle traffic signal lights convey messages only to drivers who are driving, and help drivers to stop carefully and pass other drivers easily.",
                            "ti": "ናይ ተሽከርካሪ ትራፊክ መብራት ንዝደይቡ ሻፈራት ጥራይ መልእኽቲ የሚልክ እዩ፣ ንሻፈራት ብጥንቃቄ ክደውሉን ምስ ካልኦት ሻፈራት ብቐሊሉ ክሓልፉን ይገድሎም።",
                            "or": "Ifaan mallattoo traafikii konkolaattootaa kan socho'an qofatti ergaa dhaqu, konkolaattootaas dhaabbachuufi konkolaattoota biraa darbuuf gargaaru.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "አንድ ሞተር ኃይል ለማመንጨት የሚጠቀመዉን ነዳጅ ማከማቻ ወይም ማጠራቀሚያ የሆነዉ የቱ ነዉ፡?",
                            "en": "Which one is the storage or reservoir for the fuel that an engine uses to produce power?",
                            "ti": "ሓደ ሞተር ኃይል ንምፍራይ ዝጥቀመሉ ነዳጅ እተከማቸሉ ወይ እተዓጽዎሉ እንታይ እዩ?",
                            "or": "Kana irraa kamtu qorichaa mashiinaan humna uumuuf fayyadamu itti qabamuudha?",
                            "choices": [
                                {
                                    "am": "ሳልባትዮ",
                                    "en": "Fuel tank",
                                    "ti": "ሳልባትዮ",
                                    "or": "Saalbaatioo",
                                    "is_correct": True
                                },
                                {
                                    "am": "ካርቡሬተር",
                                    "en": "Carburetor",
                                    "ti": "ካርቡሬተር",
                                    "or": "Kaarbureetara",
                                    "is_correct": False
                                },
                                {
                                    "am": "ማጣሪያ",
                                    "en": "Filter",
                                    "ti": "ማጣሪያ",
                                    "or": "Fiiltara",
                                    "is_correct": False
                                },
                                {
                                    "am": "ራዲያተር",
                                    "en": "Radiator",
                                    "ti": "ራዲያተር",
                                    "or": "Raadiyeetara",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ቤንዚን ሞተር ላይ የነዳጅና አየር ድብልቅ ማመጣጠን የሚከናወነዉ በየትኛዉ ነዉ?",
                            "en": "In a gasoline engine, where is the mixing of fuel and air balanced?",
                            "ti": "ኣብ ቤንዚን ሞተር ናይ ነዳጅን ኣየርን ምትሕውዋስ ብኸመይ እዩ ዝፍጸም?",
                            "or": "Mashiinaa banziniin keessatti, walitti makuu qorichaa fi qilleensaa eessatti raawwata?",
                            "choices": [
                                {
                                    "am": "ቦቢና",
                                    "en": "Bobina",
                                    "ti": "ቦቢና",
                                    "or": "Bobiinaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሞተሪኖ",
                                    "en": "Motorino",
                                    "ti": "ሞተሪኖ",
                                    "or": "Motorinoo",
                                    "is_correct": False
                                },
                                {
                                    "am": "ካርቡሬተር",
                                    "en": "Carburetor",
                                    "ti": "ካርቡሬተር",
                                    "or": "Kaarbureetara",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሳልባትዮ",
                                    "en": "Fuel tank",
                                    "ti": "ሳልባትዮ",
                                    "or": "Saalbaatioo",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በሞተር አካባቢ ሊሰማ የሚችልን የማይፈለግ ድምፅንና በካርቡሬተር በኩል የሚመጣን እሳት አፍኖ የሚያስቀር ክፍል የቱ ነዉ?",
                            "en": "Which part reduces engine noise and suppresses backfire coming through the carburetor?",
                            "ti": "ካብ ሞተር ዝመጽእ ዘይድለ ድምጽን ብካርቡሬተር ዝመጽእ ባርዕን ዝዓጽው ክፍሊ ኣየናይ እዩ?",
                            "or": "Qaama sagalee mashiinaa hir'isuu fi ibidda kaarbureetara keessaan dhufu ittisu kami?",
                            "choices": [
                                {
                                    "am": "አቸሬላ",
                                    "en": "Exhaust",
                                    "ti": "ኤግዛስት",
                                    "or": "Egzaastii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ቾክ",
                                    "en": "Choke",
                                    "ti": "ቾክ",
                                    "or": "Chookii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ዲብራተር (አየር ማጣሪያ)",
                                    "en": "Deburator (air filter)",
                                    "ti": "ዲብራተር (ኣየር ፍልትር)",
                                    "or": "Debureetara (fiiltaraa qilleensaa)",
                                    "is_correct": False
                                },
                                {
                                    "am": "ካርቡሬተር",
                                    "en": "Carburetor",
                                    "ti": "ካርቡሬተር",
                                    "or": "Kaarbureetara",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "በተሽከርካሪ ዉስጥ የAC ጥቅም አነስተኛ ነዉ",
                            "en": "The use of AC in a vehicle is minimal.",
                            "ti": "ኣብ ተሽከርካሪ ውሽጢ ናይ AC ተጠቒሙ ውሑድ እዩ።",
                            "or": "Fayyadama AC konkolaataa keessatti xiqqaadha.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ማሞቂያ AC ሲስተም በመጠቀም የፊት መስታወት ጭጋግ እንዲለቅ ማድረግ ይቻላል፡፡",
                            "en": "Using the heating AC system can clear fog from the front windshield.",
                            "ti": "ስርዓት ማሞቂያ AC ብምጥቃም ናይ ቅድሚት መስታውቲ ጭጋግ ክልተኽ ይከኣል።",
                            "or": "Sistiin AC ho'isaa fayyadamuu windowilee fuulaa irraa haamilee baasuu danda'a.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ አሽከርካሪ ሊከተለው የሚገባ የሥራ ቦታ ደህንነት ቅደም ተከተል ያልሆነው",
                            "en": "Which one is NOT a workplace safety procedure that a driver should follow?",
                            "ti": "ሓደ ሻፈር ክስዕቦ ዝግባእ ናይ ስራሕ ቦታ ደህንነት መስርዕ ዘይኮነ እንታይ እዩ?",
                            "or": "Kana irraa kamtu tajaajilaa eeguu qabu kan hin taane?",
                            "choices": [
                                {
                                    "am": "ንፅህና",
                                    "en": "Cleanliness",
                                    "ti": "ንፅህና",
                                    "or": "Qulqullina",
                                    "is_correct": True
                                },
                                {
                                    "am": "ትክክለኛ አለባበስ",
                                    "en": "Proper attire",
                                    "ti": "ቅኑዕ ኣለባበስ",
                                    "or": "Uffata sirrii",
                                    "is_correct": False
                                },
                                {
                                    "am": "የሥራ ቦታ ማመቻቸት",
                                    "en": "Workplace optimization",
                                    "ti": "ስራሕ ቦታ ምምሕጻእ",
                                    "or": "Bu'uura hojii sirreessuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የሥራ አካባቢን የተመቻቸ ማድረግ ማለት ምን ማለት ነዉ?",
                            "en": "What does optimizing the work environment mean?",
                            "ti": "ናይ ስራሕ ኣካባቢ ምምሕጻእ እንታይ ማለት እዩ?",
                            "or": "Bu'uura hojii sirreessuu jechuun maali?",
                            "choices": [
                                {
                                    "am": "ከርቀት የሚመጡ በጥንቃቄ ማለፍ ይችላሉ",
                                    "en": "Those coming from a distance can pass carefully",
                                    "ti": "ካብ ርሑቕ ዝመጹ ብጥንቃቄ ክሓልፉ ይኽእሉ",
                                    "or": "Namoonni fagoo irraa dhufan ariifatanii darbuu danda'u",
                                    "is_correct": True
                                },
                                {
                                    "am": "አሽከርካሪዎች ዘግይተዉ በማለፍ ላይ ላሉ እግረኞች ጥንቃቄ ማድረግ አለባቸዉ",
                                    "en": "Drivers should be careful for pedestrians crossing slowly",
                                    "ti": "ሻፈራት ንዘግይቶም ዝሓልፉ እግረኛታት ጥንቃቄ ክገብሩ ኣለዎም",
                                    "or": "Konkolaattoonni namoota piyootaan deemantu ariifatanii yoo darban, eeggachuu qabu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "SIGN",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "የሚከለክሉ እና የሚያስገድዱ የትራፊክ ምልክቶች መደባቸዉ አንድ ዓይነት ነዉ።",
                            "en": "Prohibitory and mandatory traffic signs have the same shape.",
                            "ti": "ናይ ምክልክልን ኣላስፈላጊን ትራፊክ ምልክታት ቅርጾም ሓደ እዩ።",
                            "or": "Mallattoolee traafikii dhorgaa fi dirqamaa qaamoleen isaanii wal fakkaatu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ብልጭ ድርግም የሚል ቢጫ የተሽከርካሪ ማስተላለፊያ መብራት ለብቻዉ ሲበራ የደረሰ አሽከርካሪ ፍጥነት በመቀነስ ግራና ቀኝ አይቶ ማለፍ አለበት፡፡",
                            "en": "When a yellow blinking vehicle signal light is on alone, an arriving driver must reduce speed, look left and right, and pass.",
                            "ti": "ሓንቲ ብልጭ ድርግም ኣቢላ ቢጫ ትራፊክ መብራት ምስበራ ዝበጽሐ ሻፈር ፍጥነት ብምንካስ ጸጋማይን የምሕረትን ሸነኽ ርእዩ ክሓልፍ ኣለዎ።",
                            "or": "Yoo ifaan mallattoo konkolaattootaa kelloo ta'an qofaan ibsan, konkolaataan dhufu saffisaa hir'isuun mirgaa fi bitaa ilaaluun darbuu qaba.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "በናፍጣ ሞተር በሲሊንደር ዉስጥ ናፍጣዉን (ነዳጁን) በትነት መልክ የሚረጭ ክፍል ምን ተብሎ ይጠራል?",
                            "en": "In a diesel engine, what is the part called that injects diesel fuel (the fuel) in spray form into the cylinder?",
                            "ti": "ኣብ ናፍጣ ሞተር ኣብ ውሽጢ ሲሊንደር ናፍጣ ብትንክ ቅርጺ ዝረጽኦ ክፍሊ እንታይ ይበሃል?",
                            "or": "Mashiinaa diizilii keessatti, qaamni diizilii (qorichaa) foormaa dhangala'aa ta'een siilindira keessatti dhangalaasu kami?",
                            "choices": [
                                {
                                    "am": "ኢንጀክተር ፓምፕ",
                                    "en": "Injector pump",
                                    "ti": "ኢንጀክተር ፓምፕ",
                                    "or": "Injektara paambii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ኢንጀክተር ኖዝል",
                                    "en": "Injector nozzle",
                                    "ti": "ኢንጀክተር ኖዝል",
                                    "or": "Injektara noozilii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ነዳጅ ማጣሪያ",
                                    "en": "Fuel filter",
                                    "ti": "ነዳጅ ፍልትር",
                                    "or": "Fiiltaraa qorichaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ነዳጀ መስመር",
                                    "en": "Fuel line",
                                    "ti": "ናይ ነዳጅ መስመር",
                                    "or": "Layina qorichaa",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "በናፍጣ ሞተር ላይ በመጀመሪያና በሁለተኛ ማጣሪያዎች ነዳጅ እንዲሞላ እና ከተጣራ በኋላ ወደ ኢንጀክሽን ፓምፕ በአነስተኛ ግፊት በመግፋት የሚያስተላልፍ ክፍል የቱ ነዉ?",
                            "en": "In a diesel engine, which part fills fuel in the first and second filters and after cleaning, pushes it to the injection pump with small pressure?",
                            "ti": "ኣብ ናፍጣ ሞተር ኣብ ቀዳማይን ካልኣይን ፍልትር ነዳጅ የመልእን ድሕሪ ምጽራይ ብደረት ናይ ኢንጀክሽን ፓምፕ ዝግፍፎ ክፍሊ እንታይ እዩ?",
                            "or": "Mashiinaa diizilii keessatti, qaamni kamiin qorichaa fiiltaraa tokkoffaa fi lammaffaa keessatti guutamee, ergee booda injekshinii paambii keessatti dhiqaa xiqqaa ta'een geessu?",
                            "choices": [
                                {
                                    "am": "ኢንጀክተር ኖዝል",
                                    "en": "Injector nozzle",
                                    "ti": "ኢንጀክተር ኖዝል",
                                    "or": "Injektara noozilii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ኖዝል",
                                    "en": "Nozzle",
                                    "ti": "ኖዝል",
                                    "or": "Noozilii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ኢንጀክሽን ፓምፕ",
                                    "en": "Injection pump",
                                    "ti": "ኢንጀክሽን ፓምፕ",
                                    "or": "Injekshinii paambii",
                                    "is_correct": False
                                },
                                {
                                    "am": "መጋቢ ፓመፕ",
                                    "en": "Transfer pump",
                                    "ti": "መጋቢ ፓምፕ",
                                    "or": "Paambii dhiyeessaa",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "በናፍጣ ሞተር ላይ ሲሊንደር ዉስጥ ያለን እርጥበት አዘል አየር በማሞቅ ሞተር በቀላሉ እንዲነሳ የሚያደርግ የቱ ነዉ?",
                            "en": "In a diesel engine, which one heats the moist air in the cylinder to make the engine start easily?",
                            "ti": "ኣብ ናፍጣ ሞተር ኣብ ውሽጢ ሲሊንደር ዘሎ ውሑድ ኣየር ብምውዳድ ሞተር ብቐሊሉ ንምንሳእ ዝገብር እንታይ እዩ?",
                            "or": "Mashiinaa diizilii keessatti, eessiin ho'a qilleensa dhangala'aa siilindira keessatti argamu ho'isuun mashiinaa suuta ta'ee jalqabu godhu?",
                            "choices": [
                                {
                                    "am": "ቦቢና (ኢግኒሽን ኮይል)",
                                    "en": "Bobina (ignition coil)",
                                    "ti": "ቦቢና (ኢግኒሽን ኮይል)",
                                    "or": "Bobiinaa (ignishin kooilii)",
                                    "is_correct": True
                                },
                                {
                                    "am": "ግሎዉ ፕለግ (ካንዴሊቲ)",
                                    "en": "Glow plug (candility)",
                                    "ti": "ግሎዉ ፕለግ (ካንዴሊቲ)",
                                    "or": "Gloowu plugii (kaandiliitii)",
                                    "is_correct": False
                                },
                                {
                                    "am": "ካንዴላ",
                                    "en": "Candela",
                                    "ti": "ካንዴላ",
                                    "or": "Kaandela",
                                    "is_correct": False
                                },
                                {
                                    "am": "ኖዝል",
                                    "en": "Nozzle",
                                    "ti": "ኖዝል",
                                    "or": "Noozilii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ለቤንዚንና ናፍጣ ሞተር ነዳጅ አስተላላፊ ክፍሎች መደረግ የሌለበት የቱ ነዉ",
                            "en": "Which one should NOT be done for gasoline and diesel engine fuel delivery parts?",
                            "ti": "ንቤንዚንን ናፍጣን ሞተር ነዳጅ ኣብ ዝሰግድዎ ክፍልታት ክግበር ዘይግባእ እንታይ እዩ?",
                            "or": "Qaamolee dhiyeessaa qorichaa mashiinaa banzinii fi diizilii irratti kamtu hin godhamu?",
                            "choices": [
                                {
                                    "am": "የነዳጅ መጠንን በጌጅ መከታተል",
                                    "en": "Monitoring fuel quantity with gauge",
                                    "ti": "ናይ ነዳጅ መጠን ብጌጅ ምቕታል",
                                    "or": "Gatiin qorichaa geejii wajjin ilaaluu",
                                    "is_correct": True
                                },
                                {
                                    "am": "በሳልባትዮ ዉስጥ የነዳጅ መጠን ለማወቅ እንጨት ወይም ፕላስቲክ ቱቦ መጠቀም",
                                    "en": "Using wood or plastic tube to know fuel quantity in tank",
                                    "ti": "ኣብ ሳልባትዮ ውሽጢ ናይ ነዳጅ መጠን ንምፍላጥ ዕንጨይቲ ወይ ፕላስቲክ ቱቦ ምጥቃም",
                                    "or": "Saalbaatioo keessatti gatiin qorichaa beekuuf mukaa ykn tuubaa plaastikii fayyadamu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ነዳጅ በሳልባትዮ ዉስጥ ከግማሽ በታች እንዳይሆን መከታተል",
                                    "en": "Ensuring fuel in tank is not below half",
                                    "ti": "ነዳጅ ኣብ ሳልባትዮ ውሽጢ ካብ ፍርቂ ትሕቲ ኸይኮነ ምቕታል",
                                    "or": "Qorichaan saalbaatioo keessatti walakkaa gadii hin ta'in ilaaluu",
                                    "is_correct": False
                                },
                                {
                                    "am": "በሳልባትዮ ዉስጥ እንደ ሞተሩ ዓይነት ትክክለኛ ነዳጅ መጠቀም",
                                    "en": "Using correct fuel type according to engine in tank",
                                    "ti": "ኣብ ሳልባትዮ ውሽጢ ብመሰረት ሞተር ቅኑዕ ዓይነት ነዳጅ ምጥቃም",
                                    "or": "Gosa qorichaa sirrii mashiinaa irratti hundaa'uun saalbaatioo keessatti fayyadamu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በተሽከርካሪ የነዳጅ መስመር ዉስጥ ዉሃ ወይም አየር ቢገባ የሞተር ድምፅ ይቆራረጣል፡፡",
                            "en": "If water or air enters the vehicle fuel line, the engine sound will be interrupted.",
                            "ti": "ማይ ወይ ኣየር ኣብ ናይ ተሽከርካሪ ናይ ነዳጅ መስመር እንተኣተወ ድምጺ ሞተር ይቆርጸ።",
                            "or": "Yoo bishaan ykn qilleensi layinaa qorichaa konkolaataa keessa seenee, sagaleen mashiinaa cufama.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ነዳጅ ፔዳል በመረገጥ ፍጥነት መጨመር ይቻላል፡፡",
                            "en": "Speed can be increased by pressing the accelerator pedal.",
                            "ti": "ነዳጅ ፔዳል ብምጭብባጥ ፍጥነት ክውስኽ ይከኣል።",
                            "or": "Pedala akiseeleretoraa cuunfataniin saffisa dabalchuu danda'ama.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ተሽከርካሪዎች በሚጠቀሙት የነዳጅ ዓይነት የንፋስ ወይም የዉሃ ተብለዉ ይለያሉ፡፡",
                            "en": "Vehicles are classified as air or water cooled based on the type of fuel they use.",
                            "ti": "ተሽከርካሪታት ብዝጥቀሙሉ ዓይነት ነዳጅ ንፋስ ዝተቀዘቀዘ ወይ ማይ ዝተቀዘቀዘ ኰይኖም ይፈላለፉ።",
                            "or": "Konkolaatoonni gosa qorichaa fayyadamaniin, qilleensaatiin ykn bishaantiin qabamanitti addaan baafamu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ካርቡሬተር አናት ላይ ወይም የላይኛዉ ክፍል ላይ የሚገጠም መሳሪያ የቱ ነዉ?",
                            "en": "Which device is attached to the top or upper part of the carburetor?",
                            "ti": "ኣብ ላዕሊ ካርቡሬተር ወይ ኣብ ላዕሊ ክፍሊ ዝተኣስረ መሳርያ እንታይ እዩ?",
                            "or": "Qarqaroonsi kamtu mataa kaarbureetaraa ykn qaama olka'iinsa irratti maxxanfama?",
                            "choices": [
                                {
                                    "am": "ነዳጅ ፓምፕ",
                                    "en": "Fuel pump",
                                    "ti": "ነዳጅ ፓምፕ",
                                    "or": "Paambii qorichaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ካርቡሬተር",
                                    "en": "Carburetor",
                                    "ti": "ካርቡሬተር",
                                    "or": "Kaarbureetara",
                                    "is_correct": False
                                },
                                {
                                    "am": "ነዳጅ ማጣሪያ",
                                    "en": "Fuel filter",
                                    "ti": "ነዳጅ ፍልትር",
                                    "or": "Fiiltaraa qorichaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "አየር ማጣሪያ",
                                    "en": "Air filter",
                                    "ti": "ኣየር ፍልትር",
                                    "or": "Fiiltaraa qilleensaa",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "hard",
                            "am": "ካርቡሬተር በቤንዚን ሞተር የሚገኝበት ምክንያት ለምንድን ነዉ?",
                            "en": "Why is a carburetor found in a gasoline engine?",
                            "ti": "ካርቡሬተር ኣብ ቤንዚን ሞተር ዝርከበሉ ምኽንያት ንምንታይ እዩ?",
                            "or": "Maaliif kaarbureetaraan mashiinaa banzinii keessatti argama?",
                            "choices": [
                                {
                                    "am": "ቤንዚን በቀላሉ ስለሚቆሽሽ ነዉ",
                                    "en": "Because gasoline evaporates easily",
                                    "ti": "ቤንዚን ብቐሊሉ ስለ ዝቆሸሸ",
                                    "or": "Banziniin suuta ta'ee itti dhangala'aa waan ta'eef",
                                    "is_correct": True
                                },
                                {
                                    "am": "አየርና ነዳጅ ስለሚቀላቀልበት ነዉ",
                                    "en": "Because air and fuel are mixed in it",
                                    "ti": "ኣየርን ነዳጅን ስለ ዝተቓልሐሉ",
                                    "or": "Qilleensaan fi qorichaan isa keessatti walitti makaa waan ta'eef",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Answers 1 and 2",
                                    "ti": "1 ከ 2 መልስታት እዮም",
                                    "or": "Deebii 1 fi 2",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በተሽከርካሪ ላይ የሚጫን የዕቃ ደህንነት ለመጠበቅ በዋናነት መረጃ ውስጥ መካተት ያለበት",
                            "en": "For cargo safety on a vehicle, what information should primarily be included?",
                            "ti": "ኣብ ተሽከርካሪ ዝጽዕን ጽዕነት ንምክልኻል ቀንዲ ኣብ ውሽጢ መረጃ ክንጠቀም ዘሎና እንታይ እዩ?",
                            "or": "Keesuma konkolaataa irratti ba'uuf, oduu kamtu muddama keessatti hammatuu qaba?",
                            "choices": [
                                {
                                    "am": "የዕቃው ስም",
                                    "en": "Name of the cargo",
                                    "ti": "ሽም ጽዕነት",
                                    "or": "Maqaa keesumaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ጠቅላላ ክብደ",
                                    "en": "Total weight",
                                    "ti": "ሓፈሻዊ ክብደት",
                                    "or": "Uumama waliigalaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የጭነቱ አደገኝነት",
                                    "en": "Danger level of the cargo",
                                    "ti": "ሓደገኛነት ጽዕነት",
                                    "or": "Haala bala'aa keesumaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ተሽከርካሪን ያለ እጅ ፍሬን ማቆም...... ነው",
                            "en": "Stopping a vehicle without using the hand brake is...",
                            "ti": "ተሽከርካሪ ያለ ኢድ ፍሬን ምቕጻል ... እዩ።",
                            "or": "Konkolaataa breekii harkaa hin fayyadamne dhaabbachuun... dha.",
                            "choices": [
                                {
                                    "am": "የጥንቃቄ ጉድለት",
                                    "en": "Lack of caution",
                                    "ti": "ናይ ጥንቃቄ ጉድለት",
                                    "or": "Dandeettii eeggachuu dhabuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "የዝግጁነት ጉድለት",
                                    "en": "Lack of preparedness",
                                    "ti": "ናይ ድሌት ጉድለት",
                                    "or": "Qophii dhabuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Answers 1 and 2",
                                    "ti": "1 ከ 2 መልስታት እዮም",
                                    "or": "Deebii 1 fi 2",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አደገኛ ጭነት መጫን ያለበት በየትኛዉ ተሽከርካሪ ላይ ነዉ?",
                            "en": "On which type of vehicle should dangerous cargo be loaded?",
                            "ti": "ሓደገኛ ጽዕነት ኣብ ከመይ ዓይነት ተሽከርካሪ ክጽዕን ኣለዎ?",
                            "or": "Keesuma bala'aa eessa konkolaataa irratti ba'uu qaba?",
                            "choices": [
                                {
                                    "am": "በደረቅ ጭነት(ኮንቲነር)",
                                    "en": "On dry cargo (container) vehicle",
                                    "ti": "ኣብ ደረቅ ጽዕነት (ኮንተይነር)",
                                    "or": "Konkolaataa keesumaa qallaa (kontayinarii) irratti",
                                    "is_correct": True
                                },
                                {
                                    "am": "በአውቶሞቢል",
                                    "en": "On automobile",
                                    "ti": "ኣብ መኪና",
                                    "or": "Makiinaa irratti",
                                    "is_correct": False
                                },
                                {
                                    "am": "በሕዝብ ማመላለሻ",
                                    "en": "On public transport",
                                    "ti": "ኣብ ሕዝባዊ መጋደሊ",
                                    "or": "Konkolaataa gandaawaa irratti",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "የትራፊክ አደጋ ስለደረሰበት ሰው ሪፖርት የምናደርግበት ተቋም የቱ ነው?",
                            "en": "To which institution do we report about a person involved in a traffic accident?",
                            "ti": "ትራፊክ ኣደጋ ዝገጠመሉ ሰብ ብዛዕባ ንምግላፅ ናብ ከመይ ዓይነት ትካል ሪፖርት ክንገብር ኣሎ?",
                            "or": "Namni balaan traafikii irratti hirmaate maaliif gara dhaabbataa kamiitti himuu qaba?",
                            "choices": [
                                {
                                    "am": "ቀይ መስቀል",
                                    "en": "Red Cross",
                                    "ti": "ቐይሕ መስቀል",
                                    "or": "Qixxee Diimaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ትራፊክ ፖሊስ",
                                    "en": "Traffic police",
                                    "ti": "ትራፊክ ፖሊስ",
                                    "or": "Poolisii traafikii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ኢንሹራንስ",
                                    "en": "Insurance",
                                    "ti": "ኢንሹራንስ",
                                    "or": "Inshuraansii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "HIV ኤድስ መከላከል የአሽከርካሪዎች ነው",
                            "en": "Preventing HIV/AIDS is for drivers.",
                            "ti": "ህ.ኢ.ቪ ኤድስ ምክልኻል ንሻፈራት እዩ።",
                            "or": "HIV/AIDS daranuu konkolaattootaaf.",
                            "choices": [
                                {
                                    "am": "ሃላፊነት",
                                    "en": "Responsibility",
                                    "ti": "ሓላፍነት",
                                    "or": "Hundeenna",
                                    "is_correct": True
                                },
                                {
                                    "am": "ፈቃድ",
                                    "en": "Permission",
                                    "ti": "ፈቃድ",
                                    "or": "Hayyama",
                                    "is_correct": False
                                },
                                {
                                    "am": "ግዴታ",
                                    "en": "Obligation",
                                    "ti": "ወተሃደር",
                                    "or": "Dirqama",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "HIV ኤድስ የሚተላለፍባቸው መንገዶች ዉስጥ የሚካተተዉ የቱ ነዉ",
                            "en": "Which one is included in the ways HIV/AIDS is transmitted?",
                            "ti": "ኣብቲ ህ.ኢ.ቪ ኤድስ ዝመላለስሉ መንገድታት ውሽጢ ዝኣቱ እንታይ እዩ?",
                            "or": "Kana irraa kamtu karaa HIV/AIDS darbu keessatti hammata?",
                            "choices": [
                                {
                                    "am": "በደም ንክኪ",
                                    "en": "Through blood contact",
                                    "ti": "ብርክዕ ደም",
                                    "or": "Dhiigan qunnamtii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ጥንቃቄ በጎደለው ግብረ ስጋ ግንኙነት",
                                    "en": "Through unprotected sexual intercourse",
                                    "ti": "ብዘይጥንቃቄ ግብረ ስጋ ርክብ",
                                    "or": "Qunnamtii saalaa eeggannoon ala",
                                    "is_correct": False
                                },
                                {
                                    "am": "ከእናት ወደ ልጅ",
                                    "en": "From mother to child",
                                    "ti": "ካብ ኣደ ናብ ውሉድ",
                                    "or": "Haadha irraa ilmaatti",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunda isaanii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ችግር ሲፈጠር ሐሳብን መሰብሰብ ፣ሳይበሳጩ ሁኔታዎችን በትዕግስት መከታተልና በሰላም ለመጨረስ መሞከር",
                            "en": "When a problem occurs, collect thoughts, follow situations without spreading, and try to end peacefully.",
                            "ti": "ጸገም ምስፍጠር ሓሳብ ምእካብ፣ ዘይሰፍር ኩነታት ብትዕግስት ምክትታልን ብሰላም ንምውዳእ ምፍታንን።",
                            "or": "Yoo rakkoon dhufe, yaadannoo walitti qabu, haala hin baafne ilaaluufi nagaan xumuruuf yaali.",
                            "choices": [
                                {
                                    "am": "አንድ አሽከርካሪ አማራጭ መንገዶችን ለመጠቀም ሲያወዳድር በዋናነት መርሳት የሌለበት",
                                    "en": "What a driver should not forget when comparing alternative routes",
                                    "ti": "ሓደ ሻፈር ኣማራጽ መንገድታት ምስወድድ ቀንዲ ክርስዕ ዘይግባእ",
                                    "or": "Konkolaataan karaa filannoo waliin wal bira qabu yeroo xiinxalu, waan hin irranne",
                                    "is_correct": True
                                },
                                {
                                    "am": "አንድ አሽከርካሪ ለጉዞ መያዝ ያለበት ጠቃሚ የማስረጃ ዓይነት የሆነዉ የቱ ነዉ?",
                                    "en": "What type of useful proof should a driver have for a journey?",
                                    "ti": "ሓደ ሻፈር ንጉዕዞ ክሓዝ ዘለዎ ጠቓሚ ዓይነት መርትዖ እንታይ እዩ?",
                                    "or": "Konkolaataan seenaa irratti fayyadamuuf rakkoo kam qaba?",
                                    "is_correct": False
                                },
                                {
                                    "am": "አንድ አሽከርካሪ ስለሚሄድበት መንገድ መረጃ ማግኝት የሚያስፈልገዉ ለምንድን ነዉ?",
                                    "en": "Why does a driver need to get information about the road they will travel?",
                                    "ti": "ሓደ ሻፈር ብዛዕባቲ ዝኸይዶ መንገዲ መረጃ ምርካብ ንምንታይ እዩ ዝድልዮ?",
                                    "or": "Maaliif konkolaataan oduu karaa deemuu qabu barbaacha?",
                                    "is_correct": False
                                },
                                {
                                    "am": "በጭነት ተሽከርካሪ ከኋላ ሰዎችን ትርፍ የጫነ...... ብር ይቀጣል፡፡",
                                    "en": "Loading people behind a cargo vehicle for profit... birr will be fined.",
                                    "ti": "ኣብ ድሕሪት ጽዕነት ተሽከርካሪ ሰባት ትርፊ ንምግባር ጫውዎ... ብር ይቕጸል።",
                                    "or": "Namoota konkolaataa keesumaa duubatti ba'uuf... birrii fixu.",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ሞገደኛ አሽከርካሪ ላለመሆን መደረግ ያለበት ጥንቃቄ የቱ ነዉ?",
                            "en": "What precaution should be taken to avoid being an aggressive driver?",
                            "ti": "ሞገደኛ ሻፈር ንምኽልካል ክግበር ዘለዎ ጥንቃቄ እንታይ እዩ?",
                            "or": "Konkolaataa jeeqaa ta'uu dhiisuu maal godhuu qaba?",
                            "choices": [
                                {
                                    "am": "የጉዞ ዕቅድ ማዉጣትና በቂ የጉዞ ስዓት መመደብ",
                                    "en": "Plan the trip and allocate sufficient travel time",
                                    "ti": "መደብ ጉዕዞ ምውጻእን እኹል ግዜ ጉዕዞ ምውጻእን",
                                    "or": "Karoora seenaa sirreessuu fi yeroo seenaa ga'aa qindeeffachuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "የትራፊክ መጨናነቅ በሚኖርበት ሰዓት አለመንቀሳቀስ",
                                    "en": "Avoid traveling during peak traffic hours",
                                    "ti": "ኣብቲ ትራፊክ ዝጨነቐሉ ሰዓት ኣተንቀሳቕስ",
                                    "or": "Yeroo traafikii xiqqaa ta'ee deemuu dhiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "በድካምና በብስጭት ስሜት ዉስጥ አለማሽከርከር፣ የተሽከርካሪ ዉስጣዊ ምቾት ማሻሻልና መጠበቅ",
                                    "en": "Avoid driving when tired or angry, improve and maintain vehicle interior comfort",
                                    "ti": "ኣብ ድካምን ቁጥዐን ኣተንቀሳቕስ፣ ናይ ተሽከርካሪ ውሽጣዊ ምቹነት ምምሕጻእን ምጽባትን",
                                    "or": "Yeroo rakkifanne ykn dallanne dhaquu dhiisuu, qulqullina konkolaataa keessaa sirreessuu fi tursiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ቢራ ብቻ ጠጥቶ ማሽከርከር ለአደጋ አያጋልጥም",
                            "en": "Drinking only beer and driving does not lead to accidents.",
                            "ti": "ቢራ ጥራይ ስሪሕካ ምንዳድ ኣብ ኣደጋ ኣይገብርን እዩ።",
                            "or": "Biiraa qofaa dhuganii dhaquun balaa hin fidu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ከባድ ማርሽ ፍጥነት ቀንሶ ጉልበት ይኖረዋል",
                            "en": "Heavy gear reduces speed but increases power.",
                            "ti": "ከባድ ማርሽ ፍጥነት የንክእ ግን ሓይሊ ይገብር።",
                            "or": "Geerii ulfaataan saffisaa hir'isa, humna immoo dabalsa.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "SIGN",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ከትራፊክ ፖሊስ በስተኋላ ቆመዉ የነበሩ ተሽከርካሪዎች ቀጥታ ፊት ለፊት እና ወደ ቀኝ ታጥፈዉ እንዲሄዱ የሚያዝ የእጅ ምልክት የቱ ነዉ?",
                            "en": "Which hand signal directs vehicles stopped behind traffic police to go straight ahead and turn right?",
                            "ti": "ካብ ትራፊክ ፖሊስ ድሕሪኡ ደው ዝበሉ ተሽከርካሪታት ቀጥታ ቅድሚትን ናብ የምሕረት ሸነኽን ንኺኸዱ ዝእዝዞም ኢድ ምልክት እንታይ እዩ?",
                            "or": "Mallattoon harkaa kamtu konkolaattoota poolisii traafikii duubatti dhaabbatan gara fuulduraatti fi gara mirgaatti deemuu dha?",
                            "choices": [
                                {
                                    "am": "የቀኝ እጅ ቀጥ ባለ ሁኔታ ከፍ ማድረግ",
                                    "en": "Right hand raised straight",
                                    "ti": "የምሕረት ኢድ ቀጥ ብምባል ምልዓል",
                                    "or": "Harka mirgaa gadi dhiyeessuun dhaabbachuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "የግራ እጅ ከታች ወደ ላይ ማንሳት",
                                    "en": "Left hand lifted from below upward",
                                    "ti": "ጸጋማይ ኢድ ካብ ታሕቲ ናብ ላዕሊ ምልዓል",
                                    "or": "Harka bitaa gadi dhiyeessuun dhaabbachuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁለቱን እጆች በአግድም ማስፋፋት",
                                    "en": "Both hands spread horizontally",
                                    "ti": "ክልቲኦም ኢዳት ኣብ ኣፍደገ ምስፋሕፋሕ",
                                    "or": "Harka lamaan sirriitti dhiyeessuun dhaabbachuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አንድ አሽከርካሪ ለመቆም ቢፈልግ የሚጠቀመዉ የፍሬቻ ዓይነት የቱ ነዉ?",
                            "en": "Which type of indicator does a driver use when wanting to stop?",
                            "ti": "ሓደ ሻፈር ንምዕረፍ እንተደልዩ ዝጥቀመሉ ዓይነት ፍሬቻ እንታይ እዩ?",
                            "or": "Konkolaataan yoo dhaabbachuu barbaadu, gosa ifaa mallattoo kamtiin agarsiisa?",
                            "choices": [
                                {
                                    "am": "የቀኝ",
                                    "en": "Right",
                                    "ti": "የምሕረት",
                                    "or": "Gara mirgaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "የጎን",
                                    "en": "Side",
                                    "ti": "የጎን",
                                    "or": "Gara giddii",
                                    "is_correct": False
                                },
                                {
                                    "am": "የግራ",
                                    "en": "Left",
                                    "ti": "ጸጋማይ",
                                    "or": "Gara bitaati",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "SAFETY",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የሥራ ላይ ደህንነትና ጥንቃቄ ትርጉም ያልሆነው",
                            "en": "Which is NOT the meaning of workplace safety and caution?",
                            "ti": "ኣብ ዓይነት ስራሕ ደህንነትን ኣጠንቃቕነትን ትርጕም ዘይኮነ እንታይ እዩ?",
                            "or": "Meeffannoo dhiheenya iddoo hojii fi of eeggannoo irraa maal jechuudhaaf hin fayyadamu?",
                            "choices": [
                                {
                                    "am": "አደጋን መከላከል",
                                    "en": "Preventing accidents",
                                    "ti": "ኣደጋ ምክልኻል",
                                    "or": "Bal'ina dhorguu",
                                    "is_correct": True
                                },
                                {
                                    "am": "አደጋን ሊፈጥሩ የሚችሉ ነገሮችን ማስወገድ",
                                    "en": "Eliminating things that could cause accidents",
                                    "ti": "ኣደጋ ክፈጥር ዝኽእሉ ነገራት ምውጋድ",
                                    "or": "Wanti bal'ina uumu danda'u baasuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ለአደጋ ተጋላጭ መሆን",
                                    "en": "Being exposed to danger",
                                    "ti": "ንሓደጋ ተጋላጺ ምዃን",
                                    "or": "Bal'ina irra gahuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "SAFETY",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በማሽከር ወቅት አሽክርካሪዎች ሊከተሉት የሚገባ የሥራ ላይ ደህንነት አጠባበቅ ያልሆነው",
                            "en": "Which workplace safety practice should drivers NOT follow while driving?",
                            "ti": "ሽኮርካሪታት ኣብ ዘዕለተ ስራሕ ክንቀትሉ ዘይግባእ ናይ ደህንነት ተግባር እንታይ እዩ?",
                            "or": "Hojiin dhiheenya iddoo hojii kutaa konkolaataa yeroo deemaa turan irraa kamtu hin hojjetamu?",
                            "choices": [
                                {
                                    "am": "ጤንነት ማረጋገጥ",
                                    "en": "Ensuring health",
                                    "ti": "ጥዕና ምርግጋጽ",
                                    "or": "Fayyaa mirkaneessuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ችሎታን ማወቅ",
                                    "en": "Knowing capability",
                                    "ti": "ብቕዓት ምፍላጥ",
                                    "or": "Dandeettii beekuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ተገቢ የሥራ አልባሳት መጠቀም",
                                    "en": "Using appropriate work clothes",
                                    "ti": "ግቡእ ናይ ስራሕ ክዳን ምጥቃም",
                                    "or": "Uffata hojii sirrii fayyadamu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ አሽከርካሪ ጥገና ለማከናወን ከመነሳቱ በፊት",
                            "en": "Before a driver starts to perform maintenance, what should he/she do?",
                            "ti": "ሓደ ሻፍር ምእካብ ክገብር ቅድሚ ምጅማሩ እንታይ ክገብር ኣለዎ?",
                            "or": "Konkolaataa yeroo tarkaanfii hojii godhuu eegalu maaltu godhuu qaba?",
                            "choices": [
                                {
                                    "am": "የአካባቢ ብክለት ስለ መከላከል ማወቅ አለበት",
                                    "en": "Must know about preventing environmental pollution",
                                    "ti": "ድንጋጸ ናይ ከባቢ ብክለት ክፈልጥ ኣለዎ",
                                    "or": "Dhiigina naannoo irraa eeggannoo beekuu qaba",
                                    "is_correct": True
                                },
                                {
                                    "am": "ለሥራው ተገቢ መሳሪያ ማዘጋጀት አለበት",
                                    "en": "Must prepare appropriate tools for the work",
                                    "ti": "ንስራሑ ግቡእ መሳርያ ክድልዮ ኣለዎ",
                                    "or": "Qopheessitoota sirrii hojii irratti qopheessuu qaba",
                                    "is_correct": False
                                },
                                {
                                    "am": "ለሥራው አስፈላጊ አልባሳት መጠቀም አለበት",
                                    "en": "Must use necessary work clothes",
                                    "ti": "ንስራሑ ኣድላዪ ክዳን ክጥቀም ኣለዎ",
                                    "or": "Uffata hojii barbaachisaa uffachuu qaba",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "SAFETY",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ለሥራው ተገቢውን መሳሪያ ማዘጋጀትና መጠቀም የሚለው መርህ በየትኛው የሥራ ላይደህንነት አጠባበቅ ደንብ ላይ ይገኛል?",
                            "en": "In which workplace safety rule is the principle of preparing and using appropriate tools found?",
                            "ti": "ምስራሕ ንምግባር ተገቢ መሳርያ ምድላውን ምጥቃምን ዘለዎ መሰረት ኣብ ኣየት ናይ ደህንነት ስርዓት ይርከብ?",
                            "or": "Meeffannoo qopheessuu fi fayyadamaa qopheessitoota haala ta'een taasisee hojiin dhiheenya iddoo hojii keessaa kamtu keessa jira?",
                            "choices": [
                                {
                                    "am": "በማሽከርከር ወቅት አሽከርካሪው ሊከተው የሚገባ የሥራ ላይ ደህንነት",
                                    "en": "Workplace safety that the driver should follow while driving",
                                    "ti": "ኣብ ዘዕለተ ስራሕ ሻፍር ክንቀትሎ ዘለዎ ናይ ደህንነት ስርዓት",
                                    "or": "Hojiin dhiheenya iddoo hojii konkolaataa yeroo deemaa hordofuu qabu",
                                    "is_correct": True
                                },
                                {
                                    "am": "በጥገና ወቅት አሽከርካሪው ሊከተለው የሚገባ የሥራ ላይ ደህንነት",
                                    "en": "Workplace safety that the driver should follow during maintenance",
                                    "ti": "ኣብ ዘዕለተ ምእካብ ሻፍር ክንቀትሎ ዘለዎ ናይ ደህንነት ስርዓት",
                                    "or": "Hojiin dhiheenya iddoo hojii yeroo tajaajila hojii hordofuu qabu",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Both 1 and 2 are answers",
                                    "ti": "1ን 2ን መልሲ እየን",
                                    "or": "1 fi 2 lamaan deebii dha",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ አሽከርካሪ የጉዞ መስመር ሲመርጥ ግምት ዉስጥ ማስገባት ያለበት የቱን ነዉ?",
                            "en": "What should a driver consider when choosing a travel route?",
                            "ti": "ሓደ ሻፍር መንገዲ ምርጫ ምስ ይገብር እንታይ ኣብ ግምት ክእትዉ ይግባእ?",
                            "or": "Konkolaataa yeroo karaa deemaa filatu maaltu ilaaluu qaba?",
                            "choices": [
                                {
                                    "am": "የመንገድ ዓይነትና ደረጃ",
                                    "en": "Type and condition of the road",
                                    "ti": "ዓይነትን ደረጃን መንገዲ",
                                    "or": "Gosa fi sadarkaa karaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "የመንገዱን ደህንነት ሁኔታ",
                                    "en": "Safety condition of the road",
                                    "ti": "ደህንነታዊ ኩነታት መንገዲ",
                                    "or": "Haala dhiheenyaa karaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Both 1 and 2 are answers",
                                    "ti": "1ን 2ን መልሲ እየን",
                                    "or": "1 fi 2 lamaan deebii dha",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልሱ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ አሽከርካሪ የመነሻና መድረሻ ቦታዎችን መለየት መቻሉ ለምን ይጠቅማል?",
                            "en": "Why is it useful for a driver to be able to identify departure and destination locations?",
                            "ti": "ሓደ ሻፍር መጀመርያን መድረሽን ቦታታት ክፈልጥ ምኽኣሉ ንምንታይ ይጠቅም?",
                            "or": "Maaliif konkolaataa iddoo ka'umsaa fi deebi'umsaa adda baasuu danda'uun barbaachisaa dha?",
                            "choices": [
                                {
                                    "am": "የጉዞ ስዓቱን በአግባቡ ለመወሰንና ለመጠቀም ያግዘዋል",
                                    "en": "Helps to properly determine and use travel time",
                                    "ti": "ንግዜ ጉዞ ብግቡእ ንምውሳንን ንምጥቃምን ይሕግዞ",
                                    "or": "Yeroo deemaa sirriitti murteessuu fi fayyadamuuf gargaara",
                                    "is_correct": True
                                },
                                {
                                    "am": "ድካምን ለማስወገድና በማረፊያ ቦታዎች በቂ ዕረፍት ለማድረግ ያግዘዋል",
                                    "en": "Helps to avoid fatigue and take adequate rest at resting places",
                                    "ti": "ጽምኣት ንምክልኻልን ኣብ ናይ ምዕረፍ ቦታታት እኹል ምዕረፍ ንምግባርን ይሕግዞ",
                                    "or": "Ga'umsa lakkisuu fi iddoo boqonnaa irratti boqonnaa guutuu ta'een argachuuf gargaara",
                                    "is_correct": False
                                },
                                {
                                    "am": "የተረጋጋ የማሽከርከር ክንዉን እንዲኖር ያግዘዋል",
                                    "en": "Helps to have stable driving performance",
                                    "ti": "ሰላምታ ዘለዎ ናይ ምንዳይ ውጽኢት ክህልዎ ይሕግዞ",
                                    "or": "Hojiin deemuuf tasgabbeessa ta'uu danda'uuf gargaara",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ከሚከተሉት አንዱ የመንገድ ምቹነትና ጥሩነት ይገልጻል",
                            "en": "Which one indicates the convenience and quality of the road?",
                            "ti": "ካብ እዞም ዝስዕቡ ኣንታይ እዩ ምቹነትን ጽቡቕነትን መንገዲ ዝሕብር?",
                            "or": "Kamtu miidhagina fi qulqullina karaa agarsiisa?",
                            "choices": [
                                {
                                    "am": "ብቃትና ደህንነቱ የተረጋገጠ",
                                    "en": "Its competence and safety are confirmed",
                                    "ti": "ክእለትን ደህንነትን ተረጋጊጹ",
                                    "or": "Dandeettii fi dhiheenyaan isaa mirkaneeffama",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሕጋዊ አገልግሎት መስጠት የጀመረ መሆኑ",
                                    "en": "That it has started providing legal service",
                                    "ti": "ሕጋዊ ኣገልግሎት ክህብ ጀሚሩ ምዃኑ",
                                    "or": "Tajaajila seeraan kan kennuu jalqabe ta'uu isaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "አደጋዎች በተደጋጋሚ ያስተናገደ መሆኑ",
                                    "en": "That it has repeatedly caused accidents",
                                    "ti": "ኣደጋታት ብተደጋጋሚ ዝሰግረሉ ምዃኑ",
                                    "or": "Bal'inaan yeroo baay'ee kan raawwatame ta'uu isaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Both 1 and 2 are answers",
                                    "ti": "1ን 2ን መልሲ እየን",
                                    "or": "1 fi 2 lamaan deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ አሽከርካሪ ጉዞ ከመጀመሩ በፊት የሚጓዝበትን መንገድ ባህሪያት እና የአካባቢዉን የደህንነት (ፀጥታ) ሁኔታ የሚገልጽ መረጃ ሊኖረዉ አይገባም",
                            "en": "A driver should not have information describing the road characteristics and safety (security) condition of the area before starting the journey.",
                            "ti": "ሓደ ሻፍር ጉዞ ቅድሚ ምጅማሩ ብዛዕባ ባህርያት መንገድን ናይ ከባቢ ደህንነት (ሰላም) ኩነታትን ዝገልጽ ሓበሬታ ክህልዎ ኣይግባእን።",
                            "or": "Konkolaataa yeroo deemaa eegaluu barbaachisaa ta'e karaa dhiheenyaa (nagaa) naannoo dhiheenyaa beekuu hin qabu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አንድ መረጃ ለመያዝ ቀላልና ርካሽ የሆነዉ የቱ ነዉ?",
                            "en": "Which one is easy and cheap for recording information?",
                            "ti": "ሓበሬታ ንምዝጋብ ቀሊልን ርካሽን ዝዀነ ኣየናይ እዩ?",
                            "or": "Kamtu beekumsa galmeessuuf laafaa fi herregaa dha?",
                            "choices": [
                                {
                                    "am": "ማስታወሻ ደብተር",
                                    "en": "Notebook",
                                    "ti": "ናይ ምዝገባ ደፍተር",
                                    "or": "Kitaba galmeessuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "የድምፅ መቅረጫ ቴፕሪከርደር",
                                    "en": "Voice recorder tape recorder",
                                    "ti": "ድምጺ ምዝጋብ ቴፕ ሬከርደር",
                                    "or": "Mashina sagalee galmeessuu teepii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ቪዲዮ ካሜራ",
                                    "en": "Video camera",
                                    "ti": "ቪድዮ ካሜራ",
                                    "or": "Kaameraa vidiyoo",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የጉዞ መረጃ ለማግኘት ከሚከተሉት ዉስጥ ወደ የትኛዉ መ/ቤት መሄድ ይመረጣል?",
                            "en": "To which office from the following is it advisable to go to get travel information?",
                            "ti": "ሓበሬታ ጉዞ ንምርካብ ካብ እዞም ዝስዕቡ ናብ ኣየት ቤት ኣማኸርታ ምኻድ ይግባእ?",
                            "or": "Beekumsa deemaa argachuuf daandiiwwan armaan gadii irraa kamtu gara mana hojii deemuu barbaachisaa dha?",
                            "choices": [
                                {
                                    "am": "ባንክና ኢንሹራንስ",
                                    "en": "Bank and insurance",
                                    "ti": "ባንክን ኢንሹራንስን",
                                    "or": "Baankii fi inshuuraansii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ጤና ወይም ትምህርት ቢሮ",
                                    "en": "Health or education office",
                                    "ti": "ጥዕና ወይ ትምህርቲ ቢሮ",
                                    "or": "Mana fayyaa ykn mana barnootaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ንግድና ኢንዱስትሪ ቢሮ",
                                    "en": "Trade and industry office",
                                    "ti": "ዕዮ ንግድን ኢንዱስትሪን ቢሮ",
                                    "or": "Mana daldalaa fi industria",
                                    "is_correct": False
                                },
                                {
                                    "am": "መንገድ ትራንስፖርት ቢሮ",
                                    "en": "Road transport office",
                                    "ti": "መንገዲ ትራንስፖርት ቢሮ",
                                    "or": "Mana daandii garaagaraa",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ይህ የዳሽ ቦርድ ማስጠንቀቂያ መብራት ሲበራ የነዳጅ ማጣሪያ መደፈኑን",
                            "en": "When this dashboard warning light comes on, it indicates the fuel filter is clogged.",
                            "ti": "እዚ ናይ ዳሽቦርድ ናይ ምጥንቃቕ መብራት ምስ ይበራ ፊልተር ነዳጅ ተደፊኑ ከም ዘሎ ይሕብር።",
                            "or": "Yeroo ibsaan akeekkachiisaa dash board kanaa ibsa, fiiltaraa kan bifaa dhoqqeessee jiru agarsiisa.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ከሚከተሉት አንዱ ግንኙነትን የተሳካ ለማድረግ ጠቃሚ ነዉ",
                            "en": "Which one is useful for making communication successful?",
                            "ti": "ካብ እዞም ዝስዕቡ ኣንታይ እዩ ርክብ ንምዕዋት ጠቃሚ?",
                            "or": "Kamtu qunnamtii milkaa'inaan gaggeessuuf fayyadamaa dha?",
                            "choices": [
                                {
                                    "am": "ባህል",
                                    "en": "Culture",
                                    "ti": "ባህል",
                                    "or": "Aadaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "የትምህርት ደረጃ",
                                    "en": "Education level",
                                    "ti": "ደረጃ ትምህርቲ",
                                    "or": "Sadarkaa barnootaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ኃይማኖት",
                                    "en": "Religion",
                                    "ti": "ሃይማኖት",
                                    "or": "Amantii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ከመገናኛ ቁስ ዉስጥ የማይካተተዉ የቱ ነዉ?",
                            "en": "Which one is NOT included in communication materials?",
                            "ti": "ካብ ናይ ርክብ ንብረት ውሽጢ ዘይተካተተ ኣየናይ እዩ?",
                            "or": "Kamtu qaama qunnamtii keessatti hin hammatamu?",
                            "choices": [
                                {
                                    "am": "ስዉ",
                                    "en": "Person",
                                    "ti": "ሰብ",
                                    "or": "Nama",
                                    "is_correct": True
                                },
                                {
                                    "am": "ፖስታ",
                                    "en": "Post",
                                    "ti": "ፖስታ",
                                    "or": "Poostaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ስልክ",
                                    "en": "Telephone",
                                    "ti": "ተሌፎን",
                                    "or": "Bilbila",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልሱ አልተሰጠም",
                                    "en": "Answer not given",
                                    "ti": "መልሲ ኣይተሃበን",
                                    "or": "Deebiin hin kennamne",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ከሚከተሉት ዉስጥ አንዱ አሽከርካሪ ሊያጋጥመዉ የሚችል የአደጋ ዓይነት አይደለም",
                            "en": "Which one is NOT a type of accident that a driver might encounter?",
                            "ti": "ካብ እዞም ዝስዕቡ ኣንታይ እዩ ሻፍር ክጋጥመሉ ዝኽእል ዓይነት ሓደጋ ኣይኮነን?",
                            "or": "Kamtu gosa bal'inaa konkolaataa dhaqqabuun danda'u hin taane?",
                            "choices": [
                                {
                                    "am": "የተሽከርካሪ ብልሽት",
                                    "en": "Vehicle malfunction",
                                    "ti": "ብልሽት ተሽከርካሪ",
                                    "or": "Bu'aa konkolaataa",
                                    "is_correct": True
                                },
                                {
                                    "am": "የተሽከርካሪ መጋጨት",
                                    "en": "Vehicle collision",
                                    "ti": "ምጋጫ ተሽከርካሪ",
                                    "or": "Walitti dhiibbaa konkolaataa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የእንስሳት ግጭት",
                                    "en": "Animal collision",
                                    "ti": "ምግጫ እንስሳ",
                                    "or": "Walitti dhiibbaa beyladaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የተሽከርካሪዉን የዉስጥ ምቾት ማሻሻል ማለት ምን ማለት ነዉ?",
                            "en": "What does it mean to improve the internal comfort of the vehicle?",
                            "ti": "ናይ ውሽጢ ምቾት ተሽከርካሪ ምምሕያሽ ማለት እንታይ ማለት እዩ?",
                            "or": "Miidhagina keessaa konkolaataa fooyyessuu jechuun maal jechuu dha?",
                            "choices": [
                                {
                                    "am": "አግባብነት ያለዉ የሥራ ላይ ደህንነት አጠባበቅ ነዉ",
                                    "en": "It is appropriate workplace safety practice",
                                    "ti": "ግቡእ ናይ ስራሕ ደህንነት እዩ",
                                    "or": "Hojiin dhiheenya iddoo hojii sirrii ta'ee dha",
                                    "is_correct": True
                                },
                                {
                                    "am": "አደጋ ሊፈጥሩ የሚችሉ ሁኔታዎችን መቀነስ ነዉ",
                                    "en": "It is reducing conditions that could cause accidents",
                                    "ti": "ኣደጋ ክፈጥር ዝኽእሉ ኩነታት ምንካይ እዩ",
                                    "or": "Haala bal'ina uumu danda'u hir'isuu dha",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 2 መልስ ናቸዉ",
                                    "en": "Both 1 and 2 are answers",
                                    "ti": "1ን 2ን መልሲ እየን",
                                    "or": "1 fi 2 lamaan deebii dha",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "የመንገድ ሁኔታ የሚባለዉ የቱ ነዉ?",
                            "en": "Which one is called road condition?",
                            "ti": "ኣየናይ እዩ ኩነታት መንገዲ ዚብል?",
                            "or": "Kamtu haala karaa jedhama?",
                            "choices": [
                                {
                                    "am": "ጠጠር መንገድ",
                                    "en": "Dust road",
                                    "ti": "ጠጠር መንገዲ",
                                    "or": "Karaa awwaaraa",
                                    "is_correct": True
                                },
                                {
                                    "am": "አቀበትና ቁልቁለት መንገድ",
                                    "en": "Uphill and downhill road",
                                    "ti": "ደጋዊን ቁልቁለትን መንገዲ",
                                    "or": "Karaa ol ka'aa fi gadi bu'aa",
                                    "is_correct": False
                                },
                                {
                                    "am": "አንሽራታች መንገድ",
                                    "en": "Narrow road",
                                    "ti": "ጸቢብ መንገዲ",
                                    "or": "Karaa dhiphachaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የአንድን ተሽከርካሪ ፍጥነት ለመጨመር፣ ለመቀነስና ለማቆም የሚወስነዉ የቱ ነዉ?",
                            "en": "What determines increasing, decreasing, and stopping the speed of a vehicle?",
                            "ti": "ናይ ሓደ ተሽከርካሪ ፍጥነት ንምውሳን ንምንካይን ንምሓዝን የሚወስነ ኣየናይ እዩ?",
                            "or": "Saffisa konkolaataa dabalsuu, hir'isuu fi dhaabbachuu murteessu kami?",
                            "choices": [
                                {
                                    "am": "የጭነት ሁኔታ",
                                    "en": "Load condition",
                                    "ti": "ኩነታ ጽዕነት",
                                    "or": "Haala ba'aa",
                                    "is_correct": True
                                },
                                {
                                    "am": "የአየር ሁኔታ",
                                    "en": "Weather condition",
                                    "ti": "ኩነታ ኣየር",
                                    "or": "Haala qilleensaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የትራፊክ ፍሰት ሁኔታ",
                                    "en": "Traffic flow condition",
                                    "ti": "ኩነታ ፍሰት ትራፊክ",
                                    "or": "Haala dhaabbataa traafikii",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ቁልቁለት በመዉረድ ላይ ስላለ ተሽከርካሪ ትክክል የሆነዉ የቱ ነዉ?",
                            "en": "Which is correct for a vehicle that is going downhill?",
                            "ti": "ንተሽከርካሪ ኣብ ቁልቁለት ዘሎ ቅኑዕ ኣየናይ እዩ?",
                            "or": "Kamiin sirriidha konkolaataan gara gadi bu'aa jiruuf?",
                            "choices": [
                                {
                                    "am": "አቀበት ለሚወጣዉ ቅድሚያ ይሰጣል",
                                    "en": "Gives priority to the one coming uphill",
                                    "ti": "ንዝወጽእ ኣቀበት ቅድመ ተግባር ይህቦ",
                                    "or": "Karaa ol ka'aa kan dhufuuf dursaa kenni",
                                    "is_correct": True
                                },
                                {
                                    "am": "ቁልቁለት የሚወርደዉ ቅድሚያ አለዉ",
                                    "en": "The one going downhill has priority",
                                    "ti": "ዝወርድ ቁልቁለት ቅድመ ተግባር ኣለዎ",
                                    "or": "Karaa gadi bu'aa kan jiruuf dursaa qaba",
                                    "is_correct": False
                                },
                                {
                                    "am": "ቁልቁለት የሚወርደዉ ቀላል ማርሽ መጠቀም።",
                                    "en": "The one going downhill should use light gear",
                                    "ti": "ዝወርድ ቁልቁለት ቀሊል ማርሽ ክጥቀም ኣለዎ",
                                    "or": "Karaa gadi bu'aa kan jiruuf giyaaraa laafaa fayyadamu",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 3 መልስ ናቸዉ",
                                    "en": "Both 1 and 3 are answers",
                                    "ti": "1ን 3ን መልሲ እየን",
                                    "or": "1 fi 3 lamaan deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ዳገት ላይ ያለ ተሽከርካሪን ወደ ኋላ እንዳይንሸራተት ማድረግ ያለብን የቱ ነዉ?",
                            "en": "What should we do to prevent a vehicle on a slope from rolling backward?",
                            "ti": "ኣብ ዳገት ዘሎ ተሽከርካሪ ናብ ድሕሪት ከይንሸራተቶ ንምግባር እንታይ ክንገብር ኣሎና?",
                            "or": "Maaltu gochuu qabna konkolaataan gara gadi bu'aa jiru gara dugduubatti hin deemne?",
                            "choices": [
                                {
                                    "am": "ሲነሳ ባላንስ መስራት",
                                    "en": "Use the handbrake when starting",
                                    "ti": "ምስ ይንስሓ ሃንድ ብሬክ ምግባር",
                                    "or": "Yeroo ka'uun bireekii harkaa hojjachuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሲቆም ታኮ ማድረግ ወይም የፊት ጎማ ወደ መንገድ ጠርዝ ማዞር",
                                    "en": "When stopping, use chocks or turn front wheels toward road edge",
                                    "ti": "ምስ ይደውል ታኮ ምግባር ወይ ናይ ቅድሚት መንኰራ ናብ ጫፍ መንገዲ ምዝዋር",
                                    "or": "Yeroo dhaabbatuun chokii gochuu ykn gurbaan durii gara marga karaatti garagalchuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሞተር ጠፍቶ ሲቆም አንደኛ ማርሽ ማስገባት",
                                    "en": "When stopping with engine off, put in first gear",
                                    "ti": "ሞተር ምስ ይደውል ፈሲት ቀዳማይ ማርሽ ምእታው",
                                    "or": "Yeroo dhaabbatuun injiniin cufame 1ffaa giyaaraa seensifachuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ወጣገባና ጠመዝማዛ መንገድ ምንን ያመላክታል?",
                            "en": "What do winding and zigzag roads indicate?",
                            "ti": "ወጣገባን ጠመዝማዝን መንገዲ እንታይ ይሕብር?",
                            "or": "Maaltu agarsiisa karaa gara garii fi zigzag ta'e?",
                            "choices": [
                                {
                                    "am": "የመንገድ መልካምድር",
                                    "en": "Good road surface",
                                    "ti": "ጽቡቕ ገጽ መንገዲ",
                                    "or": "Fuula karaa gaarii",
                                    "is_correct": True
                                },
                                {
                                    "am": "የመንገድ ደረጃ ዓይነት",
                                    "en": "Type of road grade",
                                    "ti": "ዓይነት ደረጃ መንገዲ",
                                    "or": "Gosa sadarkaa karaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የተለያየ የአካባቢ ሁኔታ",
                                    "en": "Different environmental conditions",
                                    "ti": "ፍልልይ ኩነታት ከባቢ",
                                    "or": "Haala naannoo adda addaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "መንጃ ፈቃድ ኖሮት ከምድብ ዉጪ ተሽከርካሪን ለሁለተኛ ጊዜ ሲያሽከረክር የተገኘ አሽከርካሪ ... ብር ይቀጣል።",
                            "en": "A driver found driving a vehicle outside his license category for the second time will be fined ... Birr.",
                            "ti": "ሻፍር ካብ ዓይነት ፍቓዱ ወጻኢ ተሽከርካሪ ንካልኣይ ግዜ ምስ የገድር ... ብር ይኽፈል።",
                            "or": "Konkolaataan giyaaraa hayyama isaa irraa ala ta'e 2ffaa yeroo argame ... Birraan baajata.",
                            "choices": [
                                {
                                    "am": "100",
                                    "en": "100",
                                    "ti": "100",
                                    "or": "100",
                                    "is_correct": True
                                },
                                {
                                    "am": "200",
                                    "en": "200",
                                    "ti": "200",
                                    "or": "200",
                                    "is_correct": False
                                },
                                {
                                    "am": "1500",
                                    "en": "1500",
                                    "ti": "1500",
                                    "or": "1500",
                                    "is_correct": False
                                },
                                {
                                    "am": "2000",
                                    "en": "2000",
                                    "ti": "2000",
                                    "or": "2000",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "በትምህርትና ስልጠና የሚገኝ ችሎታ ነዉ፡፡",
                            "en": "Ability obtained through education and training.",
                            "ti": "ብትምህርትን ስልጠናን ዚርከብ ክእለት እዩ።",
                            "or": "Dandeettii barnootaa fi aannaan argamu.",
                            "choices": [
                                {
                                    "am": "ሙያ",
                                    "en": "Profession",
                                    "ti": "ሞያ",
                                    "or": "Ogummaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሥነ-ባህሪ",
                                    "en": "Psychology",
                                    "ti": "ስነ-ባህሪ",
                                    "or": "Saayikooloojii",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሥነ-ምግባር",
                                    "en": "Ethics",
                                    "ti": "ስነ-ምግባር",
                                    "or": "Saayinsii amala",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ባለ ሞተር ተሽከርካሪ አሽከርካሪ ንቁ መሆን እና ማስተዋል አለበት፡፡",
                            "en": "A motor vehicle driver must be active and attentive.",
                            "ti": "ሻፍር ተሽከርካሪ ንቑዕን ተተኪኡን ክኸውን ኣለዎ።",
                            "or": "Konkolaataan konkolaataa dhiiga qabu sochooqaa fi eeggataa ta'uu qaba.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አሽከርካሪዎች በተሽከርካሪ ዉስጥ ሆነዉ የሚያሳዩትን ባህሪ ሳይንሳዊ በሆነ መንገድ የሚያጠና የትምህርት ዘርፍ",
                            "en": "The educational field that scientifically studies the behavior shown by drivers inside vehicles.",
                            "ti": "ናይ ትምህርቲ ዓውደ ክንዲ ኣብ ውሽጢ ተሽከርካሪ ዚርአዩ ባህርያት ሻፍርታት ብሳይንሳዊ መንገዲ ዚጽንሦ።",
                            "or": "Qaama barnootaa amala konkolaattoota konkolaataa keessatti agarsiisan saayinsii aanaan qoratu.",
                            "choices": [
                                {
                                    "am": "የማሽከርከር ሥነ ባህሪ",
                                    "en": "Driving psychology",
                                    "ti": "ስነ-ባህሪ ምንዳይ",
                                    "or": "Saayikooloojii deemsaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ባህሪ",
                                    "en": "Behavior",
                                    "ti": "ባህሪ",
                                    "or": "Amala",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሥነ ባህሪ",
                                    "en": "Psychology",
                                    "ti": "ስነ-ባህሪ",
                                    "or": "Saayikooloojii",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ የለም",
                                    "en": "No answer",
                                    "ti": "መልሲ የለን",
                                    "or": "Deebii hin jiru",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ከሚከተሉት ዉስጥ ለትራፊክ አደጋ የሚያጋልጠዉ የቱ ነዉ?",
                            "en": "Which one contributes to traffic accidents?",
                            "ti": "ካብ እዞም ዝስዕቡ ኣየናይ እዩ ንሓደጋ ትራፊክ ዜጋልጥ?",
                            "or": "Kamtu bal'ina traafikii irratti bu'aa qaba?",
                            "choices": [
                                {
                                    "am": "አልኮል መጠጥ ጠጥቶ ማሽከርከር",
                                    "en": "Drinking alcohol and driving",
                                    "ti": "ኣልኮላዊ መስተ ሰቲ ምስተ ምንዳይ",
                                    "or": "Dhaga'aa dhuguu fi deemu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ጫት ከቃሙ በኋላና እየቃሙ ማሽከርከር",
                                    "en": "Driving after taking drugs and while taking drugs",
                                    "ti": "ጫት ቅድሚ ምውሳዱን ኣብ ዘዕለተ ምውሳዱን ምንዳይ",
                                    "or": "Dhangala'aa fudhachuu booda fi yeroo fudhachuu deemu",
                                    "is_correct": False
                                },
                                {
                                    "am": "በቂ ዕረፍት አለማግኘት",
                                    "en": "Not getting enough rest",
                                    "ti": "እኹል ዕረፍቲ ኣለመርካብ",
                                    "or": "Boqonnaa guutuu ta'ee argachuu dhabuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አንድ አሽከርካሪ ጠጥቶ ካልስከረ መንዳት ይችላል፡፡",
                            "en": "A driver can drive after drinking without getting drunk.",
                            "ti": "ሓደ ሻፍር ሰቲ ሰቲ ብዘይ ምስተኽእሉ ክገድር ይኽእል እዩ።",
                            "or": "Konkolaataan dhaga'aa dhuguun kan hin darbe deemu danda'a.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ለአጭር ርቀት ጉዞ ተጠባባቂ ጎማ መያዝ አስፈላጊ ነዉ።",
                            "en": "It is necessary to carry a spare tire for short distance travel.",
                            "ti": "ንጐየያ ዝንጐይ ጉዞ ተተኪ መንኰራ ምውሳድ ኣድላዪ እዩ።",
                            "or": "Deemaa fagoo gabaabaa irratti gurbaa dhabamaa qabuun barbaachisaa dha.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "በመንገድ ላይ የሚስመሩ መስመሮች የመንገድ ጠርዝ ያመለክታሉ፡፡",
                            "en": "Lines marked on the road indicate the road edge.",
                            "ti": "ስመር ኣብ መንገዲ ዝግበር መስመራት ጫፍ መንገዲ ይሕብሩ።",
                            "or": "Daandiiwwan karaa irratti barreeffaman marga karaa agarsiisu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በመንገዱ አግድም የሚስመር መስመር መልዕክት የሆነዉ የቱ ነዉ?",
                            "en": "Which one is the message of a horizontal line marked on the road?",
                            "ti": "ኣብ መንገዲ ኣግድም ኣግድም ዝግበር መስመር መልእኽቲ ኣየናይ እዩ?",
                            "or": "Kamtu ergaa daandiiwwan karaa irratti barreeffaman horozontaalaa ta'aniidha?",
                            "choices": [
                                {
                                    "am": "የእንስሳት ማቋረጫ መሆኑን ይገልጻል",
                                    "en": "Indicates it is an animal crossing",
                                    "ti": "ናይ እንስሳት መተላለፊያ ምዃኑ ይሕብር",
                                    "or": "Karaa beyladaatiin deemuu agarsiisa",
                                    "is_correct": True
                                },
                                {
                                    "am": "የእግረኞች ማቋረጫ መሆኑን ያመላክታል",
                                    "en": "Indicates it is a pedestrian crossing",
                                    "ti": "ናይ እግረኛታት መተላለፊያ ምዃኑ ይሕብር",
                                    "or": "Karaa piidoon deemuu agarsiisa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የተሽከርካሪ ማቋረጫ መሆኑን ይገልጻል",
                                    "en": "Indicates it is a vehicle crossing",
                                    "ti": "ናይ ተሽከርካሪታት መተላለፊያ ምዃኑ ይሕብር",
                                    "or": "Karaa konkolaataatiin deemuu agarsiisa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አረንጓዴ የትራፊክ ማስተላለፊያ መብራት ከርቀት በሚታይበት ጊዜ በከፍተኛ ፍጥነት እያሽከረከረ መገናኛ መንገዱን ማቋረጥ ይገባል፡፡",
                            "en": "When a green traffic light is seen from a distance, one should cross the intersection at high speed.",
                            "ti": "ሓምላይ ናይ ትራፊክ መብራት ካብ ርሑቕ ምስ ዚርአ ብልዑል ፍጥነት እናተገደለ መገናኛ መንገዲ ክሓልፍ ይግባእ።",
                            "or": "Yeroo ibsa traafikii magariisaa fagoo irraa argame saffisa guddaan karaa walqunnamtii dhaabbachuu qaba.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አንድ አሽከርካሪ ተሽከርካሪዉን ወደ ኋላ አዙሮ ለመመለስ ቢፈልግ የትራፊክ ምልክት ሊገድበዉ አይችልም።",
                            "en": "If a driver wants to turn the vehicle around to go back, traffic signs cannot prohibit him/her.",
                            "ti": "ሓደ ሻፍር ተሽከርካሪ ናብ ድሕሪት ምእንቲ ክመልስ ምስ ይደልይ ምልክት ትራፊክ ከይግድዶ ኣይክእልን እዩ።",
                            "or": "Yoo konkolaataan gara dugduubatti deebi'uun barbaade, mallattoon traafikii isa dhorguu hin danda'u.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ለመሄድ ተዘጋጅ የሚል የትራፊክ ማስተላለፊያ መብራት የቱ ነዉ?",
                            "en": "Which traffic light means 'get ready to go'?",
                            "ti": "ናይ ትራፊክ መብራት ንምንታይ እዩ 'ንምንታይ ተዳለው' ዝብል?",
                            "or": "Kamtu ibsa traafikii 'deemuuf qophaa'i' jechuudha?",
                            "choices": [
                                {
                                    "am": "ቢጫ",
                                    "en": "Yellow",
                                    "ti": "ቢጫ",
                                    "or": "Kelloo",
                                    "is_correct": True
                                },
                                {
                                    "am": "ቀይና ቢጫ",
                                    "en": "Red and yellow",
                                    "ti": "ቀይን ቢጫን",
                                    "or": "Diimaa fi kelloo",
                                    "is_correct": False
                                },
                                {
                                    "am": "አረንጓዴ",
                                    "en": "Green",
                                    "ti": "ሓምላይ",
                                    "or": "Magariisaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ቀይ",
                                    "en": "Red",
                                    "ti": "ቀይ",
                                    "or": "Diimaa",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ቢጫ ብልጭ ድርግም የሚል የትራፊክ መብራት ሲበራ ፍጥነት በመቀነስ ግራና ቀኝ አይተን እንድናልፍ ያዛል፡፡",
                            "en": "When a yellow blinking traffic light comes on, it instructs us to reduce speed and look left and right before crossing.",
                            "ti": "ቢጫ ዓውዲ ዓውዲ ዝብል ናይ ትራፊክ መብራት ምስ ይበራ ፍጥነት ብምንካይ ጸጋማይን የምንትን ኣይተና ክንሓልፍ ይእዝዘና።",
                            "or": "Yeroo ibsa traafikii kellaa dhaammachaa ibsa, saffisa hir'iisuu fi mirgaafi bitaa ilaaluu karaa dhaabbachuun nu ajaja.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ቀይ የትራፊክ መብራት ብልጭ ድርግም ሲል የደረስ አሽከርካሪ ፍጥነቱን ቀንሶ ማለፍ አለበት",
                            "en": "When a red traffic light blinks, a driver who has arrived should reduce speed and pass.",
                            "ti": "ቀይ ናይ ትራፊክ መብራት ምስ ይብልጭ ድርግም ዝደረሸ ሻፍር ፍጥነቱ ብምንካይ ክሓልፍ ኣለዎ።",
                            "or": "Yeroo ibsa traafikii diimaa dhaammacha, konkolaataan dhufee jiru saffisa hir'iisuu fi dhaabbachuu qaba.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ቢጫ የተሽከርካሪ ማስተላለፊያ መብራት ሲበራ ወደ መገናኛ መንገድ የገባ ተሽከርካሪ ማድረግ የሚገባዉ",
                            "en": "When a yellow vehicle traffic light comes on, what should a vehicle that has entered the intersection do?",
                            "ti": "ቢጫ ናይ ተሽከርካሪታት መብራት ምስ ይበራ ናብ መገናኛ መንገዲ ዝኣተወ ተሽከርካሪ እንታይ ክገብር ኣለዎ?",
                            "or": "Yeroo ibsa traafikii kellaa konkolaataa ibsa, konkolaataan gara karaa walqunnamtii seenu maaltu godhuu qaba?",
                            "choices": [
                                {
                                    "am": "ተሽከርካሪዉን ወደ ኋላ መመለስ ይገባዋል",
                                    "en": "Should reverse the vehicle",
                                    "ti": "ተሽከርካሪ ናብ ድሕሪት ክመልስ ኣለዎ",
                                    "or": "Konkolaataan gara dugduubatti deebi'uu qaba",
                                    "is_correct": True
                                },
                                {
                                    "am": "ቆሞ ተሽከርካሪዉን ማሳለፍ አለበት",
                                    "en": "Should stop and let the vehicle pass",
                                    "ti": "ደው ኢሉ ተሽከርካሪ ክሓልፍ ኣለዎ",
                                    "or": "Dhaabbachuu fi konkolaataa dhaabbachuu qaba",
                                    "is_correct": False
                                },
                                {
                                    "am": "በፍጥነት መንገዱን ለቆ መዉጣት አለበት",
                                    "en": "Should quickly leave the intersection",
                                    "ti": "ብቕልጡፍ መንገዲ ብምትሕብባር ክወጽእ ኣለዎ",
                                    "or": "Achumaan karaa dhaabbachuu fi ba'uu qaba",
                                    "is_correct": False
                                },
                                {
                                    "am": "ተሽከርካሪዎች ጋር ተቀላቅሎ መጓዝ",
                                    "en": "Should continue with other vehicles",
                                    "ti": "ምስ ካልኦት ተሽከርካሪታት ተተሓሒዙ ክጓዓዝ ኣለዎ",
                                    "or": "Konkolaattoota biroo waliin deemuu qaba",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ረድፍን ለመለወጥ መደረግ ያለበት የቱ ነዉ?",
                            "en": "Which one should be done to change lanes?",
                            "ti": "ረድፍ ንምቕያር እንታይ ክግበር ኣለዎ?",
                            "or": "Kamtu gochuu qaba karaa jijjiiramuuf?",
                            "choices": [
                                {
                                    "am": "ፍሬቻ ማሳየት",
                                    "en": "Showing turn signal",
                                    "ti": "ፍሬቻ ምርኣይ",
                                    "or": "Firiichaa agarsiisuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሃዛርድ ማብራት",
                                    "en": "Turning on hazard lights",
                                    "ti": "ሓደገኛ መብራት ምብራህ",
                                    "or": "Ibsa bal'aa ibsaa",
                                    "is_correct": False
                                },
                                {
                                    "am": "የፍሬን መብራት ማሳየት",
                                    "en": "Showing brake lights",
                                    "ti": "መብራት ፍሬን ምርኣይ",
                                    "or": "Ibsa bireekii agarsiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልስ አልተሰጠም",
                                    "en": "Answer not given",
                                    "ti": "መልሲ ኣይተሃበን",
                                    "or": "Deebiin hin kennamne",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ከተሽከርካሪ የኋላ መብራቶች ዉስጥ ነጩ መብራት የሚበራዉ መቼ ነዉ?",
                            "en": "When does the white light among the rear lights of a vehicle come on?",
                            "ti": "ካብ ናይ ድሕሪት መብራት ተሽከርካሪ ውሽጢ ጻዕዳ መብራት መዓስ እዩ ዚበራ?",
                            "or": "Yoomuu ibsa adii gurbaa dugduubaa konkolaataa keessaa ibsa?",
                            "choices": [
                                {
                                    "am": "የኋላ ማርሽ ስናስገባ",
                                    "en": "When we engage reverse gear",
                                    "ti": "ድሕሪት ማርሽ ምስ ንእተው",
                                    "or": "Yeroo giyaaraa dugduubaa seensifannu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ፍሬን ስንይዝ",
                                    "en": "When we apply brakes",
                                    "ti": "ፍሬን ምስ ንዝው",
                                    "or": "Yeroo bireekii harkaa qabnu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መኪና ስናቆም",
                                    "en": "When we stop the car",
                                    "ti": "መኪና ምስ ንደውል",
                                    "or": "Yeroo konkolaataa dhaabbannu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ፍሬቻ ስናበራ",
                                    "en": "When we turn on turn signals",
                                    "ti": "ፍሬቻ ምስ ንበራ",
                                    "or": "Yeroo firiichaa ibsannu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አንድ አሽከርካሪ አቅጣጫዉን ከመለወጡ ወይም ከመታጠፉ በፊት ፍሬቻ ወይም የእጅ ምልክት ማሳየት አለበት",
                            "en": "A driver should show turn signal or hand signal before changing direction or turning.",
                            "ti": "ሓደ ሻፍር ኣገዳሲ ኣገዳሲ ወይ ኢድ ምልክት ቅድሚ ምቕያር ወይ ቅድሚ ምትላል ክርእዮ ኣለዎ።",
                            "or": "Konkolaataan mallattoo gara jijjiiramuu ykn harka agarsiisuu qaba yeroo gara jijjiiramuu ykn gara jijjiiramuu eegalu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ከቆምንበት ከመነሳት ወይም ጉዞ ከመጀመራችን በፊት ከኋላ የአካባቢዉን ሁኔታ በስፖኪዮ መመልከት ያስፈልጋል፡፡",
                            "en": "We need to check the condition behind us using mirrors before moving from a stop or starting a journey.",
                            "ti": "ካብ ዝደውልና ቦታ ቅድሚ ምንሻሕና ወይ ጉዞ ቅድሚ ምጅማርና ንኹነታት ድሕሪት ብማይክሮስኮፕ ክንርእዮ የድልየና።",
                            "or": "Yeroo dhaabbannaa irraa socho'uu ykn deemaa eegaluu dura haala duubaa ilaaluu qabna miirraawwan fayyadamuun.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "RULES",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አንድን ተሽከርካሪ ለመቅደም ስንፈልግ በቅድሚያ በስፖኪዮ አማካኝነት ከኋላ እና ከጎን ተሽከርካሪ አለመኖሩን ማረጋገጥ ይገባል፡፡",
                            "en": "When we want to overtake a vehicle, we should first confirm using mirrors that there is no vehicle behind and beside.",
                            "ti": "ሓደ ተሽከርካሪ ንምቕዳም ምስ ንደሊ ቀዳማይ ብማይክሮስኮፕ ድሕሪትን ጎንን ተሽከርካሪ ከም ዘይብሉ ንምርግጋጽ ኣለና።",
                            "or": "Yeroo konkolaataa dursaa nu barbaadnu, dura miirraawwan fayyadamuun konkolaataa duubaa fi gaditti hin jirreetti mirkaneeffachuu qabna.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ሞተር የሚቀዘቅዝበት ዘዴ የትኛዉ ነዉ?",
                            "en": "Which is the method by which the engine is cooled?",
                            "ti": "ሞተር ዚጽግዕ ኣገባብ ኣየናይ እዩ?",
                            "or": "Meeffannoowwan injiniin qorraa'u kamtu dha?",
                            "choices": [
                                {
                                    "am": "አየር",
                                    "en": "Air",
                                    "ti": "ኣየር",
                                    "or": "Qilleensa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ነዳጅ",
                                    "en": "Fuel",
                                    "ti": "ነዳጅ",
                                    "or": "Bifa",
                                    "is_correct": False
                                },
                                {
                                    "am": "ዉሃ",
                                    "en": "Water",
                                    "ti": "ማይ",
                                    "or": "Bishaan",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 3 መልስ ናቸዉ፡፡",
                                    "en": "Both 1 and 3 are answers",
                                    "ti": "1ን 3ን መልሲ እየን",
                                    "or": "1 fi 3 lamaan deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በሞተር ዉስጥ ዉሃ በግፊት እንዲዘዋወር የሚያደርግ ክፍል የቱ ነዉ?",
                            "en": "Which part makes water circulate under pressure in the engine?",
                            "ti": "ኣብ ውሽጢ ሞተር ማይ ብግፊት ንኺዘዋወር ዝገብር ክፍሊ ኣየናይ እዩ?",
                            "or": "Qaama bishaan injiniina keessatti dhiibbaan deemu godhu kami?",
                            "choices": [
                                {
                                    "am": "የዉሃ ፓምፕ",
                                    "en": "Water pump",
                                    "ti": "ፓምፕ ማይ",
                                    "or": "Paampii bishaan",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሪዘርቨር (ኤክስፓንሽን ታንከር)",
                                    "en": "Reservoir (expansion tank)",
                                    "ti": "ሪዘርቨር (ኤክስፓንሽን ታንክ)",
                                    "or": "Reezarvoo (taankii expandishinii)",
                                    "is_correct": False
                                },
                                {
                                    "am": "ራዲያተር",
                                    "en": "Radiator",
                                    "ti": "ራዲያተር",
                                    "or": "Raadiyeetara",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሆዝ",
                                    "en": "Hose",
                                    "ti": "ሆዝ",
                                    "or": "Hoozii",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አካል ጉዳተኞች ከመኪና ሲወርዱም ሆነ ሲወጡ መደገፍ ወይም መንከባከብ ተገቢ ነዉ።",
                            "en": "It is appropriate to support or assist persons with disabilities when they get out of or into a car.",
                            "ti": "ኣካላዊ ጉዳት ዘለዎም ሰባት ካብ መኪና ምስ ይወርዱ ወይ ምስ ይኣቱ ምድጋፍ ወይ ምሕጋዝ ግቡእ እዩ።",
                            "or": "Namoota rakkoo qaban yeroo konolaataa irraa ba'an ykn seenan gargaarsa ykn gargaarsa gochuu sirrii dha.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "በሀገራችን ለአካል ጉዳተኞች እንዲያመች ተብሎ የሚዘጋጅ የትራንስፖርት አገልግሎት በጣም ዝቅተኛ ነዉ",
                            "en": "In our country, transport services prepared to accommodate persons with disabilities are very limited.",
                            "ti": "ኣብ ሃገርና ንኣካላዊ ጉዳት ዘለዎም ሰባት ንምምላእ እተዳለወ ናይ ትራንስፖርት ኣገልግሎት ኣዝዩ ውሑድ እዩ።",
                            "or": "Biyya keenyatti tajaajila daandiiwwan namoota rakkoo qabanuf qophaa'e gahaa ta'aniin xiqqaa dha.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "ማንኛዉንም ተሽከርካሪ ጠዋት ጠዋት ሞተር አስነስተን ከ5 እስከ 15 ደቂቃ በሚኒሞ (አይድል) ማሰራት ለምን አስፈለገ?",
                            "en": "Why is it necessary to start any vehicle in the morning and let it run at idle (idle) for 5 to 15 minutes?",
                            "ti": "ንኹሉ ተሽከርካሪ ንግሆ ሞተር ምስ ንምስካብ ካብ 5 ክሳብ 15 ደቒቕ ብሚኒሞ (ኣይድል) ምስራቱ ስለምንታይ እዩ ዜድልዮ?",
                            "or": "Maaliif konkolaataa hunda bariisaa injiniin kaasuu fi dhiigaa 5 hanga 15 daqiiqaa tura (idle) gochuu barbaachisaa dha?",
                            "choices": [
                                {
                                    "am": "ሞተር በበቂ ደረጃ እንዲሞቅና ተገቢ ጉልበት እንዲሰጠን",
                                    "en": "So that the engine warms up sufficiently and gives us proper power",
                                    "ti": "ሞተር ብብጽግት ንኺውዕልን ግቡእ ሓይሊ ንኺህበናን",
                                    "or": "Injiniin guutuu ta'een ho'aachuu fi humna sirrii nuuf kennuuf",
                                    "is_correct": True
                                },
                                {
                                    "am": "በሞተር ዉስጥ ያለዉ የሞተር ዘይት በየሲስተሙ እንዲዘዋወር ለማድረግ",
                                    "en": "To make the engine oil inside the engine circulate throughout the system",
                                    "ti": "ኣብ ውሽጢ ሞተር ዘሎ ዘይቲ ሞተር ኣብ ኩሉ ሲስተም ንኺዘዋወር",
                                    "or": "Zayitii injiniina injiniina keessaa jiru sistamii guutuutti deemuuf",
                                    "is_correct": False
                                },
                                {
                                    "am": "በራዲያር ዉስጥ ያለዉ ቀዝቃዛ ዉሃ መካከለኛ ሙቀት እንዲኖረዉ",
                                    "en": "So that the cold water in the radiator reaches medium temperature",
                                    "ti": "ኣብ ራዲያተር ዘሎ ዝሑል ማይ ማእከላይ ዋዕደ ንኺህልዎ",
                                    "or": "Bishaan qorraa'aa raadiyeetara keessaa jiru ho'aa giddu galeessa ta'ee argachuuf",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም መልስ ነዉ",
                                    "en": "All are answers",
                                    "ti": "ኩሎም መልሲ እዮም",
                                    "or": "Hunduu deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ለረዥም ጊዜ ሲሰራ የነበረን የተሽከርካሪ ሞተር ወዲያዉኑ ማጥፋት ለሞተር ክፍሎች መበላሸት ምክንያት ይሆናል፡፡",
                            "en": "Turning off a vehicle engine immediately after it has been working for a long time will cause damage to engine parts.",
                            "ti": "ሞተር ተሽከርካሪ ንነዊሕ ግዜ ምስ ይሰርሕ ብኡንብኡ ምጥፋኡ ንክፍልታት ሞተር ምብላሽ ምኽንያት ክኸውን ይኽእል እዩ።",
                            "or": "Injiniin konkolaataa yeroo dheeraaf hojjatee booda dhaqaaqaa isaa cufuun qaama injiniinaa balleessuuf sababa ta'a.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "የራዲያተር ዉሃ ከልክ በላይ ሲሞቅ አደጋ እንዳይደርስ በቀላሉ ክዳኑን ከፍቶ ዉሃ መሙላት ይቻላል፡፡",
                            "en": "When radiator water overheats, to prevent danger, you can simply open its cap and fill it with water.",
                            "ti": "ማይ ራዲያተር ካብ ዓቐኑ ምስ ይውዕል ሓደጋ ከየጋጥመልና በቲ ዓቐኑ ብቐሊሉ ክንክፍቶን ማይ ክንምላኦን ንኽእል ኢና።",
                            "or": "Yeroo bishaan raadiyeetaraa ho'aa ol ta'e bal'inaa irraa eegaluuf laafaan qophii isaa bannee bishaan guutuu danda'a.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "የተሽከርካሪ ሞተር ከፍተኛ ሙቀት በሚያሳይበት ወቅት ሞተር አጥፍተን ወዲያዉኑ ቀዝቃዛ ዉሃ መጨመር ይቻላል፡፡",
                            "en": "When a vehicle engine shows high temperature, you can turn off the engine and immediately add cold water.",
                            "ti": "ሞተር ተሽከርካሪ ልዑል ዋዕደ ምስ ይርኢ ሞተር ክንጥፍኦን ብኡንብኡ ዝሑል ማይ ክንወስዶን ንኽእል ኢና።",
                            "or": "Yeroo injiniin konkolaataa ho'aa ol ta'e agarsiise injiniin cufuu fi bishaan qorraa'aa dhaqaaqaa isaa dabaluu danda'a.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀሰት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "ሞተር በሞቀ ወቅት የዉሃና የዘይት መጠን ለማየት ወዲያዉኑ ክዳኖቹን ከፍቶ ማየት ይቻላል፡፡",
                            "en": "When the engine is hot, you can immediately open their caps to check the amount of water and oil.",
                            "ti": "ሞተር ምስ ይውዕል ብዓቐን ማይን ዘይትን ንምርኣይ ብኡንብኡ ክዳኖም ክንክፍቶን ክንርእዮን ንኽእል ኢና።",
                            "or": "Yeroo injiniin ho'aa jiru, safara bishaanii fi zayitaa ilaaluuf qophii isaanii bannee ilaaluu danda'a.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "VEHICLE",
                            "sign": None,
                            "img": None,
                            "diff": "easy",
                            "am": "አዲስ ተሽከርካሪ ላይ የራዲያተር ዉሃን በየጊዜዉ ማየት አያስፈልግም፡፡",
                            "en": "On a new vehicle, you don't need to check the radiator water regularly.",
                            "ti": "ኣብ ሓድሽ ተሽከርካሪ ማይ ራዲያተር ብየግዜኡ ንምርኣይ ኣየድልየንን እዩ።",
                            "or": "Konkolaataa haaraa irratti bishaan raadiyeetaraa yeroo yeroo ilaaluun hin barbaachisu.",
                            "choices": [
                                {
                                    "am": "እዉነት",
                                    "en": "True",
                                    "ti": "ሀቅዩ",
                                    "or": "Deebii",
                                    "is_correct": True
                                },
                                {
                                    "am": "ሀስት",
                                    "en": "False",
                                    "ti": "ስሕተት",
                                    "or": "Dogoggora",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አደጋን ተከላክሎ ለማሽከርከር ማድረግ ከሚገባን ትክክል የሆነዉ የቱ ነዉ?",
                            "en": "Which one is correct for what we should do to drive safely?",
                            "ti": "ኣደጋ ብምክልኻል ንምንዳይ ክንገብር ዘሎና ቅኑዕ ኣየናይ እዩ?",
                            "or": "Kamiin sirriidha dhiheenyaan deemuuf gochuu qabnu irratti?",
                            "choices": [
                                {
                                    "am": "በፍጥነት ማሽከርከር",
                                    "en": "Driving fast",
                                    "ti": "ብቕልጡፍ ምንዳይ",
                                    "or": "Saffisaan deemu",
                                    "is_correct": True
                                },
                                {
                                    "am": "በተሽከርካሪዎች መካከል ያለዉን ርቀት መጠበቅ",
                                    "en": "Maintaining distance between vehicles",
                                    "ti": "ኣብ መንጎ ተሽከርካሪታት ዘሎ ርሕቀት ምግባር",
                                    "or": "Fagoo konkolaattoota gidduu jiru tursiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "የትራፊክ ምልክቶችን አለማክበር",
                                    "en": "Not obeying traffic signs",
                                    "ti": "ምልክት ትራፊክ ኣይንብብን",
                                    "or": "Mallattoo traafikii hin kabajne",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም መልስ ነዉ",
                                    "en": "All are answers",
                                    "ti": "ኩሎም መልሲ እዮም",
                                    "or": "Hunduu deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "የሰከንድ ህግ ማለት ምንን ይገልጻል?",
                            "en": "What does the 'two-second rule' indicate?",
                            "ti": "'ሕጊ ክልተ ሰከንድ' እንታይ ይገልጽ?",
                            "or": "'Seera sekondii lama' maal agarsiisa?",
                            "choices": [
                                {
                                    "am": "ተከታትለን የምንጓዝበት ርቀት ያመለክታል",
                                    "en": "Indicates the distance we follow while driving",
                                    "ti": "ኣብ ዘዕለተ ምንዳይና ንዚንቀትሎ ርሕቀት ይሕብር",
                                    "or": "Fagoo nuti yeroo deemnu hordofnu agarsiisa",
                                    "is_correct": True
                                },
                                {
                                    "am": "በፍጥነት የምናሽከረክርበት ህግ ነዉ",
                                    "en": "It is a law about how fast we drive",
                                    "ti": "ኣብ ዝንዳድ ፍጥነት ዚምልከት ሕጊ እዩ",
                                    "or": "Seera saffisaan nuti deemnu dha",
                                    "is_correct": False
                                },
                                {
                                    "am": "በፍጥነት የምንቀድምበት ህግ ነዉ",
                                    "en": "It is a law about how fast we overtake",
                                    "ti": "ኣብ ዝንቀድም ፍጥነት ዚምልከት ሕጊ እዩ",
                                    "or": "Seera saffisaan nuti dursaa deemnu dha",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልሱ አልተሰጠም",
                                    "en": "Answer not given",
                                    "ti": "መልሲ ኣይተሃበን",
                                    "or": "Deebiin hin kennamne",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አደጋ በደረሰበት ቦታ ተጨማሪ አደጋ እንዳይከስት ምን መደረግ አለበት?",
                            "en": "What should be done at the accident site to prevent additional accidents?",
                            "ti": "ኣብቲ ሓደጋ ኣብ ዝገበረሉ ቦታ ተወሳኺ ሓደጋ ከየጋጥመልና እንታይ ክግበር ኣሎ?",
                            "or": "Maaltu gochuu qaba iddoo bal'inaa irratti bal'ina dabalataa hin uumne?",
                            "choices": [
                                {
                                    "am": "ሃዛርድ መብራት ማብራት",
                                    "en": "Turning on hazard lights",
                                    "ti": "ሓደገኛ መብራት ምብራህ",
                                    "or": "Ibsa bal'aa ibsaa",
                                    "is_correct": True
                                },
                                {
                                    "am": "ርቀትን ጠብቆ ማሽከርከር",
                                    "en": "Driving while maintaining distance",
                                    "ti": "ርሕቀት ብምግባር ምንዳይ",
                                    "or": "Fagoo tursiisuu fi deemu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሦስት መአዘን አንፀባራቂ ምልክት ማስቀመጥ",
                                    "en": "Placing three reflective triangle signs",
                                    "ti": "ሰለስተ ማዕዘን ዝነጸረ ምልክት ምቕማጥ",
                                    "or": "Mallattoo sadiin giraafiliksii ta'een kaasuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "1 እና 3 መልስ ናቸዉ",
                                    "en": "Both 1 and 3 are answers",
                                    "ti": "1ን 3ን መልሲ እየን",
                                    "or": "1 fi 3 lamaan deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አሽከርካሪዎች ሲያሽከረክሩ አደጋ እንዳያደርሱ መዉሰድ የሚገባቸዉ ጥንቃቄ የቱ ነዉ?",
                            "en": "Which precaution should drivers take while driving to avoid causing accidents?",
                            "ti": "ሻፍርታት ኣብ ዘዕለተ ምንዳዮም ሓደጋ ከየፍጥሩ ክወስዱ ዘለዎም ኣጠንቃቕነት ኣየናይ እዩ?",
                            "or": "Eeggannoon konkolaattoota yeroo deemaa bal'ina hin uumneef fudhatamu kami?",
                            "choices": [
                                {
                                    "am": "ፍጥነታቸዉን መቆጣጠር",
                                    "en": "Controlling their speed",
                                    "ti": "ፍጥነቶም ምቆጣጠር",
                                    "or": "Saffisa isaanii ti'uu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ተሽከርካሪን መፈተሽ",
                                    "en": "Checking the vehicle",
                                    "ti": "ተሽከርካሪ ምፍታሽ",
                                    "or": "Konkolaataa qorachuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "የመንገዱን ሁኔታ አስቀድሞ መረዳት",
                                    "en": "Understanding the road condition in advance",
                                    "ti": "ኩነታት መንገዲ ቅድሚ ምጅማር ምፍላጥ",
                                    "or": "Haala karaa dura beekuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አሽከርካሪዎች ከኋላ በኩል የሚደርሰዉን ግጭት ለመከላከል ሊያደርጉት የሚገባ የቱ ነዉ",
                            "en": "What should drivers do to prevent rear-end collisions?",
                            "ti": "ሻፍርታት ካብ ድሕሪት ዚመጽእ ምግጫ ንምክልኻል እንታይ ክገብሩ ኣለዎም?",
                            "or": "Maaltu gochuu qabu konkolaattoota dhiibbaa duubaa irraa eegaluuf?",
                            "choices": [
                                {
                                    "am": "ከኋላ ያለዉን ዕይታ መቆጣጠር",
                                    "en": "Monitoring the view behind",
                                    "ti": "ናይ ድሕሪት ምርኣይ ምቆጣጠር",
                                    "or": "Duubaa ilaaluu",
                                    "is_correct": True
                                },
                                {
                                    "am": "የኋላ መስታወት ንፅህና መጠበቅ",
                                    "en": "Keeping the rear mirror clean",
                                    "ti": "መስተውዒ ድሕሪት ጽሩይ ምግባር",
                                    "or": "Miroorii duubaa qulqullina tursiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ከመታጠፍ ወይም ረድፍ ከመቀየር በፊት በምልክት ማሳወቅ",
                                    "en": "Giving signal before turning or changing lanes",
                                    "ti": "ቅድሚ ምትላል ወይ ረድፍ ቅድሚ ምቕያር ብምልክት ምፍላጢ",
                                    "or": "Yeroo gara jijjiiramuu ykn karaa jijjiiramuu eegaluu mallattoo kennuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አሽከርካሪዎች ሌሎች ተሽከርካሪዎችን ለመቅደም ሲፈልጉ ሊያደርጉት የሚገባ ጥንቃቄ",
                            "en": "What caution should drivers take when they want to overtake other vehicles?",
                            "ti": "ሻፍርታት ካልኦት ተሽከርካሪታት ክቕድሙ ምስ ደልዮም ክወስዱ ዘለዎም ኣጠንቃቕነት ኣየናይ እዩ?",
                            "or": "Eeggannoon konkolaattoota yeroo konkolaattoota biroo dursaa barbaadan fudhatamu kami?",
                            "choices": [
                                {
                                    "am": "መቅደም የሚቻለዉ በቀኝ በኩል መሆኑን መገንዘብ",
                                    "en": "Understanding that overtaking is only allowed on the right side",
                                    "ti": "ምቕዳም ኣብ የማን ሸነኽ ጥራይ ከም ዝከኣል ምርዳእ",
                                    "or": "Dursaa deemuu gara mirgaa qofa dhaabbata jechuun hubachuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ከፊት ለፊት በተቃራኒ አቅጣጫ የሚመጣን ተሽከርካሪ ፍጥነት ማገናዘብ",
                                    "en": "Estimating the speed of oncoming vehicles",
                                    "ti": "ካብ ቅድሚት ብተጻራሪ ኣገዳሲ ዝመጽእ ተሽከርካሪ ፍጥነት ምግምታጥ",
                                    "or": "Saffisa konkolaataa gara faanaa kan dhufu muruu",
                                    "is_correct": False
                                },
                                {
                                    "am": "በበቂ ጊዜና ርቀት ላይ የቀኝ ፍሬቻ ማሳየት",
                                    "en": "Showing right turn signal with sufficient time and distance",
                                    "ti": "ብእኹል ግዜን ርሕቀትን የማን ፍሬቻ ምርኣይ",
                                    "or": "Yeroo fi fagoo guutuutti firiichaa mirgaa agarsiisuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ አሽከርካሪ የመንገደኞች ዕቃ በሚጫንበት ጊዜ ማወቅ ያለበት ዓብይ ነጥብ",
                            "en": "What is the main point a driver should know when loading passengers' luggage?",
                            "ti": "ሻፍር ኣብ ዘዕለተ ጽዕነት መንገደኛታት ዚጽዕኖ ዓብዪ ነጥብ እንታይ እዩ?",
                            "or": "Guyyaa konkolaataa ba'aa imaaltota geggeessaa jiru beekuu qabu maal dha?",
                            "choices": [
                                {
                                    "am": "ዕቃዉ በደንብ የታስረና የታሸገ መሆኑን ማረጋገጥ",
                                    "en": "Ensuring the luggage is properly tied and covered",
                                    "ti": "ጽዕነት ብግቡእ ከም ዝተሰርዐን ከም ዝተኸወነን ምርግጋጽ",
                                    "or": "Ba'aan sirriitti hidhamee fi haguuggamee jiru mirkaneeffachuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ዕቃዉ ተሰባሪ መሆንና አለመሆኑን መለየት",
                                    "en": "Identifying whether the luggage is fragile or not",
                                    "ti": "ጽዕነት ዕንደራ ከም ዝኸውን ወይ ኣይኰነን ምፍላጥ",
                                    "or": "Ba'aan dhangala'aa ta'uu isaa fi hin taane adda baasuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ዕቃዉ በቀላሉ ሊበላሽ የሚችል መሆንና አለመሆኑን ማወቅ",
                                    "en": "Knowing whether the luggage is easily breakable or not",
                                    "ti": "ጽዕነት ብቐሊሉ ከም ዝበላሽ ወይ ኣይኰነን ምፍላጥ",
                                    "or": "Ba'aan laafaan balleessuu danda'uu isaa fi hin dandeenye beekuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አሽከርካሪዎች ከቦታ ወደ ቦታ በሚንቀሳቀሱበት ጊዜ ለሁሉም የሕብረተሰብ ክፍል ማድረግ ያለባቸዉ",
                            "en": "What should drivers do for all segments of society when moving from place to place?",
                            "ti": "ሻፍርታት ካብ ቦታ ናብ ቦታ ምስ ይንቀሳቀሱ ንኹሉ ክፍሊ ሕብረተሰብ እንታይ ክገብሩ ኣለዎም?",
                            "or": "Maaltu gochuu qabu konkolaattoota yeroo iddoo irraa iddoo birootti deeman waantaalee hawaasaa hunda irratti?",
                            "choices": [
                                {
                                    "am": "አክብሮት መስጠት",
                                    "en": "Giving respect",
                                    "ti": "ቅቡል ምሃብ",
                                    "or": "Kabajaa kennuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "ለሁሉም እኩል ፍቅር መስጠት",
                                    "en": "Giving equal love to all",
                                    "ti": "ንኩሎም እኩል ፍቕሪ ምሃብ",
                                    "or": "Jaalala walqixxaa hundaaf kennuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ታማኝ መሆን",
                                    "en": "Being honest",
                                    "ti": "ርትዓውነት ምዃን",
                                    "or": "Ammasummaa ta'uu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "በትራንስፖርት ዘርፍ የተሰማራ አንድ አሽከርካሪ ሊያዉቃቸዉና ሊተገብራቸዉ ከሚገቡ ዋና ዋና ጉዳዮች ዉስጥ የማይካተተዉ የቱ ነዉ?",
                            "en": "Which one is NOT among the main issues that a driver working in the transport sector should know and apply?",
                            "ti": "ካብቲ ኣብ ዘርፍ ትራንስፖርት ዝሰርሕ ሻፍር ክፈልጦን ክተግብሮን ዘለዎ ቀንዲ ቀንዲ ጉዳያት ውሽጢ ዘይተካተተ ኣየናይ እዩ?",
                            "or": "Kamtu irraa hin taane dhimmi gugurdoo konkolaataan tajaajila daandiiwwan irratti hojjatu beekuu fi fayyadamuuf qabu keessaa?",
                            "choices": [
                                {
                                    "am": "የአካባቢዉን ዕሴት ማወቅ",
                                    "en": "Knowing the value of the area",
                                    "ti": "ትርጉም ከባቢ ምፍላጥ",
                                    "or": "Waa'ee naannoo beekuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "የአካባቢዉን ኃይማኖት መረዳት",
                                    "en": "Understanding the religion of the area",
                                    "ti": "ሃይማኖት ከባቢ ምርዳእ",
                                    "or": "Amantii naannoo hubachuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "የሕብረተሰቡን ባህል ማወቅ",
                                    "en": "Knowing the culture of the society",
                                    "ti": "ባህል ሕብረተሰብ ምፍላጥ",
                                    "or": "Aadaa hawaasaa beekuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "መልሱ አልተሰጠም",
                                    "en": "Answer not given",
                                    "ti": "መልሲ ኣይተሃበን",
                                    "or": "Deebiin hin kennamne",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ አሽከርካሪ ለአካል ጉዳተኞች የማድረግ ግዴታ የሌለበት ተግባር የቱ ነዉ?",
                            "en": "Which action is a driver NOT obliged to do for persons with disabilities?",
                            "ti": "ሓደ ሻፍር ንኣካላዊ ጉዳት ዘለዎም ሰባት ክገብር ዘይግዴታ ዝኾነ ተግባር ኣየናይ እዩ?",
                            "or": "Hojiin konkolaataan namoota rakkoo qaban irratti gochuu hin qabu kami?",
                            "choices": [
                                {
                                    "am": "ከታሪፍ በታች እንዲከፍሉ ማድረግ",
                                    "en": "Making them pay below tariff",
                                    "ti": "ካብ ታሪፍ ትሕቲ ንኺኽፍሉ ምግባር",
                                    "or": "Tariffii gadii ta'een kaffalu isaan gochuu",
                                    "is_correct": True
                                },
                                {
                                    "am": "እንዳይንገላቱ ረጋ ብሎ ማሽከርከር",
                                    "en": "Driving slowly so they don't get shaken",
                                    "ti": "ከይንግለቱ ቀስ ብበለ ምንዳይ",
                                    "or": "Isaan hin shokkinne haala ta'een saffisa hir'isuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "የቅድሚያ ትኬት እንዲያገኙ ማድረግ",
                                    "en": "Making them get priority tickets",
                                    "ti": "ቅድመ ተግባር ትኬት ንኺረኽቡ ምግባር",
                                    "or": "Tikii dursaa argachuu isaan gochuu",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም",
                                    "en": "All of the above",
                                    "ti": "ኩሎም",
                                    "or": "Hunduu",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        },
                        {
                            "type": "TT",
                            "cat": "GENERAL",
                            "sign": None,
                            "img": None,
                            "diff": "medium",
                            "am": "አንድ የሕዝብ ትራንስፖርት የሚያሽከረክር አሽከርካሪ ጉዞ ከመጀመሩ በፊት ማወቅ ያለበት የቱ ነዉ?",
                            "en": "What should a public transport driver know before starting a journey?",
                            "ti": "ሓደ ሻፍር ሕዝባዊ ትራንስፖርት ጉዞ ቅድሚ ምጅማሩ እንታይ ክፈልጥ ኣለዎ?",
                            "or": "Maaltu beekuu qaba konkolaataan tajaajila daandiiwwan ummataa yeroo deemaa eegaluu dura?",
                            "choices": [
                                {
                                    "am": "ዕቅድ እና የጉዞ መስመር ካርታ ማወቅ አለበት",
                                    "en": "Must know the plan and travel route map",
                                    "ti": "መደብን ካርታ መንገዲ ጉዞን ክፈልጥ ኣለዎ",
                                    "or": "Karooraa fi kaartaa karaa deemaa beekuu qaba",
                                    "is_correct": True
                                },
                                {
                                    "am": "የመንገዱን ባህሪያትና የአካባቢዉን ደህንነት ማወቅ አለበት",
                                    "en": "Must know the road characteristics and area safety",
                                    "ti": "ባህርያት መንገዲን ደህንነት ከባቢን ክፈልጥ ኣለዎ",
                                    "or": "Amala karaa fi dhiheenyaa naannoo beekuu qaba",
                                    "is_correct": False
                                },
                                {
                                    "am": "አደጋ በሚያጋጥም ጊዜ መረጃ የሚያስተላልፍለትን አካል ማወቅ አለበት",
                                    "en": "Must know the body to report to when an accident occurs",
                                    "ti": "ሓደጋ ምስ ይጋጥም ሓበሬታ ንዚልክቶ ኣካል ክፈልጥ ኣለዎ",
                                    "or": "Yeroo bal'ina ta'e qaama odeeffannoo isaaf dhiheessu beekuu qaba",
                                    "is_correct": False
                                },
                                {
                                    "am": "ሁሉም መልስ ናቸዉ",
                                    "en": "All are answers",
                                    "ti": "ኩሎም መልሲ እዮም",
                                    "or": "Hunduu deebii dha",
                                    "is_correct": False
                                }
                            ],
                            "explanation": {
                                "media_url": "https://youtube.com/...",
                                "media_type": "video",
                                "am": "ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።",
                                "en": "This is the correct answer because it follows Ethiopian traffic regulations.",
                                "ti": "እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።",
                                "or": "Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."
                            }
                        }
                    ]

        question_objs = []

        for q in questions:
            question = Question.objects.create(
                category=category_objs[q["cat"]],
                associated_road_sign=q.get("sign"),
                media_image=q.get("img"),
                question_type=q["type"],
                difficulty=q["diff"]
            )
            question_objs.append(question)

            for lang in ['en', 'am', 'ti', 'or']:
                if lang in q:
                    QuestionTranslation.objects.create(
                        question=question,
                        language=lang,
                        content=q[lang]
                    )

            if "choices" in q and isinstance(q["choices"], list):
                choices_bulk = []
                translations_bulk = []

                for order, choice_data in enumerate(q["choices"]):
                    ch = AnswerChoice(
                        question=question,
                        is_correct=choice_data.get("is_correct", False),
                        order=order
                    )
                    choices_bulk.append(ch)

                created_choices = AnswerChoice.objects.bulk_create(choices_bulk)

                for ch_obj, choice_data in zip(created_choices, q["choices"]):
                    for lang in ['en', 'am', 'ti', 'or']:
                        if lang in choice_data:
                            translations_bulk.append(
                                AnswerChoiceTranslation(
                                    answer_choice=ch_obj,
                                    language=lang,
                                    text=choice_data[lang]
                                )
                            )

                if translations_bulk:
                    AnswerChoiceTranslation.objects.bulk_create(translations_bulk)

            if "explanation" in q and isinstance(q["explanation"], dict):
                exp_data = q["explanation"]
                exp = Explanation.objects.create(
                    question=question,
                    media_url=exp_data.get("media_url"),
                    media_type=exp_data.get("media_type", "text")
                )
                ExplanationTranslation.objects.bulk_create([
                    ExplanationTranslation(explanation=exp, language=lang, detail=exp_data[lang])
                    for lang in ['en', 'am', 'ti', 'or']
                    if lang in exp_data
                ])


        # ===================================================================
        # 7. Exams
        # ===================================================================

        exams = [
            {"en": "Free Practice Exam",    "am": "ነጻ ልምምድ ፈተና",               "ti": "ፈተና ልምዲ ብዝክፈለ",               "or": "Tapha Fayyadamummaa Bilisaa",     "free": True,  "pass": 70},
            {"en": "Basic Driving Test",    "am": "መሰረታዊ መንጃ ፈተና",            "ti": "ፈተና መንጃ መባእታ",               "or": "Tapha Mooraa Bu'uuraa",          "free": False, "pass": 74},
            {"en": "Advanced Road Rules Exam","am": "የላቀ የመንገድ ህግ ፈተና",       "ti": "ፈተና ህግያት መንገዲ ላቀ",         "or": "Tapha Seera Margaa Ol'aanaa",    "free": False, "pass": 74},
        ]

        exam_objs = []

        import random
        random.seed(42)   # for reproducible results during development

        all_questions = question_objs[:]   # copy

        for ex in exams:
            exam = Exam.objects.create(
                difficulty="medium",
                duration_minutes=30 if ex["free"] else 60,
                question_count=20 if ex["free"] else 50,
                passing_score=ex["pass"],
                is_free=ex["free"]
            )
            exam_objs.append(exam)

            for lang in ['en', 'am', 'ti', 'or']:
                ExamTranslation.objects.create(
                    exam=exam,
                    language=lang,
                    title=ex[lang],
                    description=f"{ex[lang]} — {'free practice' if ex['free'] else 'certification'} exam"
                )

            n_questions = 20 if ex["free"] else 50

            if len(all_questions) < n_questions:
                selected = all_questions[:]
            elif ex["free"]:
                selected = all_questions[:n_questions]
            else:
                selected = random.sample(all_questions, n_questions)

            exam.questions.set(selected)


        # Link exams to tiers / packages
        if len(exam_objs) >= 3:
            tier_objs[0].exams.add(exam_objs[0])           # free
            tier_objs[1].exams.add(exam_objs[1])
            tier_objs[2].exams.add(exam_objs[2])
            # if you have more exams → decide how to assign them


        self.stdout.write(self.style.SUCCESS(
            f"Complete seeding finished successfully! "
            f"({len(question_objs)} questions, {len(exam_objs)} exams created)"
        ))