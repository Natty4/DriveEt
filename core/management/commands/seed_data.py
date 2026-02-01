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
            # ...
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