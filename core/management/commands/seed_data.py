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
                'en': "Traffic Rules",
                'am': "የትራፊክ ደንቦች",
                'ti': "ስርዓተ ትራፊክ",
                'or': "Seera Margaa"
            },
            'VEHICLE': {
                'en': "Vehicle Handling",
                'am': "ተሽከርካሪ አያያዝ",
                'ti': "ኣተኣኻኽብ ተሽከርካሪ",
                'or': "Qabinsa Mooraa"
            },
            'PEDESTRIAN': {
                'en': "Pedestrian Safety",
                'am': "የእግረኛ ደህንነት",
                'ti': "ሓለዋ እግረኛ",
                'or': "Nagaa Namoota Margaa"
            },
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
                "code": "YIELD_001",
                "image": "road_signs/yield.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "Yield", "meaning": "Give way to other traffic", "detailed_explanation": "Slow down and be ready to stop if necessary to let other vehicles pass."},
                    "am": {"name": "መብት ስጡ", "meaning": "ለሌላ ተሽከርካሪ መብት ይስጡ", "detailed_explanation": "ቀስ በበሉ እና አስፈላጊ ከሆነ ሌሎች ተሽከርካሪዎች እንዲያልፉ ለመቆም ይዘጋጁ።"},
                    "ti": {"name": "ኣፍቅሩ", "meaning": "ካልእ ተሽከርካሪ ቅድሚያ ሃቡ", "detailed_explanation": "ቀስ ብበሉን ኣብ ዘድልየሉ እዋን ካልእ ተሽከርካሪ ክሳጠር ንኽእትዉ ደው ክትብሉ ይዳሎ።"},
                    "or": {"name": "Kennuu", "meaning": "Margaa biraa kennuu", "detailed_explanation": "Suuta dhaabi jedhuun of eeggadhu fi mooraa biraa dabarsuuf barbaachise dhaabuu."}
                }
            },
            {
                "code": "SPEED_50",
                "image": "road_signs/speed_50.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "Speed Limit 50", "meaning": "Maximum speed is 50 km/h", "detailed_explanation": "Do not exceed 50 km/h in this zone."},
                    "am": {"name": "ፍጥነት ገደብ 50", "meaning": "ከፍተኛው ፍጥነት 50 ኪ.ሜ/ሰ ነው", "detailed_explanation": "በዚህ ቀጠና ከ50 ኪ.ሜ/ሰ አይበልጥም።"},
                    "ti": {"name": "ፍጥነት ገደብ 50", "meaning": "ዝለዓለ ፍጥነት 50 ኪሎሜትር/ሰዓት", "detailed_explanation": "ኣብዚ ዞባ ካብ 50 ኪሎሜትር/ሰዓት ኣይትበልጽ።"},
                    "or": {"name": "Safuu 50", "meaning": "Safuu ol aanaa 50 km/h", "detailed_explanation": "Naannoo kana keessatti 50 km/h irra caaluu hin qabu."}
                }
            },
            {
                "code": "NO_HORN",
                "image": "road_signs/no_horn.png",
                "category": rs_cat_objs['REGULATORY'],
                "translations": {
                    "en": {"name": "No Horn", "meaning": "Honking is prohibited", "detailed_explanation": "Do not use your horn in this area."},
                    "am": {"name": "ሆርን አትጠቀሙ", "meaning": "ሆርን መጫን የተከለከለ ነው", "detailed_explanation": "በዚህ አካባቢ ሆርን አይጠቀሙ።"},
                    "ti": {"name": "ሆርን ኣይትጥቀሙ", "meaning": "ሆርን መጠቀም ዝተከልከለ", "detailed_explanation": "ኣብዚ ከባቢ ሆርን ኣይትጥቀሙ።"},
                    "or": {"name": "Hojii Hin Gochuu", "meaning": "Hojii gochuu dhorkame", "detailed_explanation": "Naannoo kana keessatti hojii gochuu hin danda'amu."}
                }
            },
            {
                "code": "PEDESTRIAN",
                "image": "road_signs/pedestrian.png",
                "category": rs_cat_objs['WARNING'],
                "translations": {
                    "en": {"name": "Pedestrian Crossing", "meaning": "Pedestrians may be crossing", "detailed_explanation": "Be prepared to stop for pedestrians."},
                    "am": {"name": "የእግረኛ መሻገሪያ", "meaning": "እግረኞች ሊያቋሽጡ ይችላሉ", "detailed_explanation": "ለእግረኞች ለመቆም ይዘጋጁ።"},
                    "ti": {"name": "መሻገሪ እግረኛ", "meaning": "እግረኛታት ክሳጠሩ ይኽእሉ", "detailed_explanation": "ንእግረኛታት ንደው ክትብሉ ይዳሎ።"},
                    "or": {"name": "Ce'umsaa Namootaa", "meaning": "Namoonni marga ce'uun danda'u", "detailed_explanation": "Namoota margaa ce'uuf of eeggadhu."}
                }
            },
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
            {"price": 0, "days": 0, "max_exams": 1, "full_quiz": False,
             "en": "Free Plan", "am": "ነጻ ፓኬጅ", "ti": "ፕላን ብዝክፈለ", "or": "Paakeejii Bilisaa"},
            {"price": 100, "days": 30, "max_exams": 5, "full_quiz": True,
             "en": "Basic Monthly", "am": "መሰረታዊ ወርሃዊ", "ti": "መባእታ ወርሒ", "or": "Ji'a Bu'uuraa"},
            {"price": 250, "days": 90, "max_exams": 15, "full_quiz": True,
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

        # ===================================================================
        # 6. 15 Realistic Questions (all 4 languages)
        # ===================================================================
        questions = [
            {
                "type": "IT", "cat": "SIGN", "sign": sign_objs[0], "img": None, "diff": "easy",
                "en": "What does this road sign mean?",
                "am": "ይህ የመንገድ ምልክት ምን ማለት ነው?",
                "ti": "እዚ ምልክት መንገዲ እንታይ ማለት እዩ?",
                "or": "Mallattoon margaa kun maal jechuudha?"
            },
            {
                "type": "TI", "cat": "SIGN", "sign": None, "img": "questions/pedestrian_crossing.png", "diff": "medium",
                "en": "Which sign indicates a pedestrian crossing ahead?",
                "am": "የእግረኛ መሻገሪያ መኖሩን የሚያመለክተው የትኛው ምልክት ነው?",
                "ti": "መሻገሪ እግረኛ ኣብ ቅድሚ ዘሎ ዝኣመልክት መንታ ምልክት እዩ?",
                "or": "Mallattoon kamtu ce'umsaa namootaa dursee jiraachuu agarsiisa?"
            },
            {
                "type": "TT", "cat": "RULES", "sign": None, "img": None, "diff": "medium",
                "en": "What is the maximum speed limit in urban areas in Ethiopia?",
                "am": "በኢትዮጵያ በከተማ ውስጥ ከፍተኛው ፍጥነት ገደብ ስንት ነው?",
                "ti": "ኣብ ኢትዮጵያ ኣብ ከተማ ዝለዓለ ፍጥነት ገደብ መንእዩ?",
                "or": "Itiyoophiyaa keessatti magaala keessatti ol aanaa safuu baay'ina ciicannoo maalidha?"
            },
            {
                "type": "IT", "cat": "SIGN", "sign": sign_objs[1], "img": None, "diff": "easy",
                "en": "What should you do when you see this sign?",
                "am": "ይህን ምልክት ሲያዩ ምን ማድረግ አለብዎት?",
                "ti": "እዚ ምልክት ምስ ትርእዩ እንታይ ክትገብሩ ይግባእ?",
                "or": "Mallattoo kana argite yoom maal gochuu qabda?"
            },
            {
                "type": "TT", "cat": "VEHICLE", "sign": None, "img": None, "diff": "hard",
                "en": "When must you use your headlights during the day?",
                "am": "በቀን ውስጥ የፊት መብራቶችዎን መቼ መጠቀም አለብዎት?",
                "ti": "ኣብ መዓልቲ መብራህቲ ቅድሚ መቼ ክትጥቀሙ ይግባእ?",
                "or": "Guyyaa keessatti ifa mooraa kee yoom fayyadamuu qabda?"
            },
            {
                "type": "TT", "cat": "RULES", "sign": None, "img": None, "diff": "medium",
                "en": "Who has the right of way at an uncontrolled intersection?",
                "am": "በቁጥጥር ያልተደረገበት መገናኛ ላይ መብት ያለው ማን ነው?",
                "ti": "ኣብ መገናኒ ቁጽጽር ዘይብሉ መብት መን እዩ?",
                "or": "Walqunnamtii qabuun hin qabne keessatti eenyu qaba?"
            },
            {
                "type": "IT", "cat": "SIGN", "sign": sign_objs[2], "img": None, "diff": "easy",
                "en": "What is the speed limit shown on this sign?",
                "am": "በዚህ ምልክት ላይ የተጠቀሰው ፍጥነት ገደብ ስንት ነው?",
                "ti": "ኣብዚ ምልክት ዝተጠቅሰ ፍጥነት ገደብ መንእዩ?",
                "or": "Mallattoo kana irratti safuu baay'ina ciicannoo kam agarsiisa?"
            },
            {
                "type": "TT", "cat": "PEDESTRIAN", "sign": None, "img": None, "diff": "medium",
                "en": "When should you yield to pedestrians?",
                "am": "እግረኞችን መብት መስጠት መቼ ነው?",
                "ti": "ንእግረኛታት መብት ክትህቡ መቼ እዩ?",
                "or": "Namoonni margaa yoom kennuu qabda?"
            },
            {
                "type": "TI", "cat": "SIGN", "sign": None, "img": "questions/no_entry.png", "diff": "easy",
                "en": "Which sign means 'No Entry'?",
                "am": "የትኛው ምልክት 'መግባት ክልል' ማለት ነው?",
                "ti": "መንታ ምልክት 'መግባት ክልል' ማለት እዩ?",
                "or": "Mallattoon kamtu 'Seenuun Hin Danda’amu' jechuudha?"
            },
            {
                "type": "TT", "cat": "VEHICLE", "sign": None, "img": None, "diff": "hard",
                "en": "What should you do if your vehicle starts to skid?",
                "am": "ተሽከርካሪዎ መንሸራተት ከጀመረ ምን ማድረግ አለብዎት?",
                "ti": "ተሽከርካሪኻ እንተተንስሓረ እንታይ ክትገብር ይግባእ?",
                "or": "Mooraa kee yoo jalqabe yoom maal gochuu qabda?"
            },
            {
                "type": "IT", "cat": "SIGN", "sign": sign_objs[3], "img": None, "diff": "medium",
                "en": "What does this sign prohibit?",
                "am": "ይህ ምልክት ምንን ይከለክላል?",
                "ti": "እዚ ምልክት እንታይ ይከላኸል?",
                "or": "Mallattoon kun eenyu dhorkaa?"
            },
            {
                "type": "TT", "cat": "RULES", "sign": None, "img": None, "diff": "easy",
                "en": "At a roundabout, who has priority?",
                "am": "በመጠገቢያ ክብ ውስጥ መብት ያለው ማን ነው?",
                "ti": "ኣብ መጠገቢያ ክብ መብት መን እዩ?",
                "or": "Qubee margaa keessatti eenyu qaba?"
            },
            {
                "type": "TI", "cat": "SIGN", "sign": None, "img": "questions/school_zone.png", "diff": "medium",
                "en": "Which sign warns of a school zone ahead?",
                "am": "የትምህርት ቤት ቀጠና መኖሩን የሚያስጠነቅቀው የትኛው ምልክት ነው?",
                "ti": "መንታ ምልክት ቅድሚ ቤተ ትምህርቲ ከባቢ ኣመልክት?",
                "or": "Mallattoon kamtu mana barumsaa dursee jiraachuu akeekkachiisa?"
            },
            {
                "type": "TT", "cat": "VEHICLE", "sign": None, "img": None, "diff": "hard",
                "en": "What is the correct following distance on highways?",
                "am": "በአውራ ጎዳናዎች ላይ ትክክለኛው የመከተል ርቀት ስንት ነው?",
                "ti": "ኣብ ናይ መንገዲ ዓበይቲ ትክክለኛ ርቐት መከተት መንእዩ?",
                "or": "Karaa mooraa guddaa irratti safuu ulfaatina yoomidha?"
            },
            {
                "type": "IT", "cat": "SIGN", "sign": sign_objs[4], "img": None, "diff": "easy",
                "en": "What does this warning sign indicate?",
                "am": "ይህ ማስጠንቀቂያ ምልክት ምን ያመለክታል?",
                "ti": "እዚ ምልክት ማስጠንቀቕያ እንታይ የመልክት?",
                "or": "Mallattoon akeekkachiisaa kun maal agarsiisa?"
            },
        ]

        question_objs = []
        for q in questions:
            question = Question.objects.create(
                category=category_objs[q["cat"]],
                associated_road_sign=q["sign"],
                media_image=q["img"],
                question_type=q["type"],
                difficulty=q["diff"]
            )
            question_objs.append(question)

            # Translations
            for lang in ['en', 'am', 'ti', 'or']:
                QuestionTranslation.objects.create(
                    question=question,
                    language=lang,
                    content=q[lang]
                )

            # 4 Answer Choices (first is correct)
            choices = [
                ("Correct answer", "ትክክለኛ መልስ", "ትክክለኛ መልስ", "Deebii sirrii"),
                ("Incorrect option A", "ስህተት አማራጭ ሀ", "ስሕተት ምርጫ ሀ", "Dogoggora A"),
                ("Incorrect option B", "ስህተት አማራጭ ለ", "ስሕተት ምርጫ ለ", "Dogoggora B"),
                ("Incorrect option C", "ስህተት አማራጭ ሐ", "ስሕተት ምርጫ ሐ", "Dogoggora C"),
            ]
            for j, (en_text, am_text, ti_text, or_text) in enumerate(choices):
                choice = AnswerChoice.objects.create(
                    question=question,
                    is_correct=(j == 0),
                    order=j
                )
                AnswerChoiceTranslation.objects.bulk_create([
                    AnswerChoiceTranslation(answer_choice=choice, language='en', text=en_text),
                    AnswerChoiceTranslation(answer_choice=choice, language='am', text=am_text),
                    AnswerChoiceTranslation(answer_choice=choice, language='ti', text=ti_text),
                    AnswerChoiceTranslation(answer_choice=choice, language='or', text=or_text),
                ])

            # Explanation
            exp = Explanation.objects.create(
                question=question,
                media_url="https://youtube.com/example_explanation",
                media_type="video"
            )
            ExplanationTranslation.objects.bulk_create([
                ExplanationTranslation(explanation=exp, language='en', detail="This is the correct answer because it follows Ethiopian traffic regulations."),
                ExplanationTranslation(explanation=exp, language='am', detail="ይህ ትክክለኛ መልስ ነው ምክንያቱም የኢትዮጵያ ትራፊክ ደንቦችን ይከተላል።"),
                ExplanationTranslation(explanation=exp, language='ti', detail="እዚ ትክክለኛ መልስ እዩ ምኽንያቱ ስርዓተ ትራፊክ ኢትዮጵያ ይከተል።"),
                ExplanationTranslation(explanation=exp, language='or', detail="Kuni deebii sirrii waan ta'eef seera margaa Itiyoophiyaa kan hordofu."),
            ])

        # ===================================================================
        # 7. Exams (3)
        # ===================================================================
        exams = [
            {"en": "Free Practice Exam", "am": "ነጻ ልምምድ ፈተና", "ti": "ፈተና ልምዲ ብዝክፈለ", "or": "Tapha Fayyadamummaa Bilisaa", "free": True, "pass": 70},
            {"en": "Basic Driving Test", "am": "መሰረታዊ መንጃ ፈተና", "ti": "ፈተና መንጃ መባእታ", "or": "Tapha Mooraa Bu'uuraa", "free": False, "pass": 74},
            {"en": "Advanced Road Rules Exam", "am": "የላቀ የመንገድ ህግ ፈተና", "ti": "ፈተና ህግያት መንገዲ ላቀ", "or": "Tapha Seera Margaa Ol'aanaa", "free": False, "pass": 80},
        ]

        exam_objs = []
        for ex in exams:
            exam = Exam.objects.create(
                difficulty="medium",
                duration_minutes=30 if not ex["free"] else 20,
                question_count=50 if not ex["free"] else 30,
                passing_score=ex["pass"],
                is_free=ex["free"]
            )
            exam_objs.append(exam)

            for lang in ['en', 'am', 'ti', 'or']:
                ExamTranslation.objects.create(
                    exam=exam,
                    language=lang,
                    title=ex[lang],
                    description=f"{ex[lang]} — practice exam"
                )

            exam.questions.set(question_objs)

        # Link exams to tiers
        tier_objs[0].exams.add(exam_objs[0])
        tier_objs[1].exams.add(exam_objs[1])
        tier_objs[2].exams.add(exam_objs[2])

        self.stdout.write(self.style.SUCCESS("Complete seeding finished successfully!"))