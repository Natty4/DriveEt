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
                "code": "NOENTRY_001",
                "image": "road_signs/no_entry.png",
                "category": rs_cat_objs["REGULATORY"],
                "translations": {
                    "en": {"name": "No Entry", "meaning": "Entry prohibited", "detailed_explanation": "Do not enter this road or area. Usually found at one-way streets or restricted zones."},
                    "am": {"name": "መግባት አይፈቀድም", "meaning": "መግባት የተከለከለ ነው", "detailed_explanation": "ወደዚህ መንገድ ወይም አካባቢ አትግቡ። ብዙውን ጊዜ በአንድ አቅጣጫ መንገድ ወይም የተገደበ አካባቢ ይገኛል።"},
                    "ti": {"name": "እቶን ኣይፍቀድ", "meaning": "እቶን ተኸልኪሉ ኣሎ", "detailed_explanation": "ናብዚ መገዲ ወይ ከባቢ ኣይተኣቱ። መብዛሕትኡ ግዜ ኣብ ሓደ ኣንፈት መገዲ ወይ ዝተዓጸወ ከባቢ ይርከብ።"},
                    "or": {"name": "Seenuu Hin Dandeenye", "meaning": "Seenuu hin eeggamu", "detailed_explanation": "Karaa ykn naannoo kana seenuu hin dandeessu. Yeroo baay'ee karaa tokkicha ykn naannoo harkifame keessatti argama."}
                }
            },
            {
                "code": "NOOVERT_002",
                "image": "road_signs/no_overtaking.png",
                "category": rs_cat_objs["REGULATORY"],
                "translations": {
                    "en": {"name": "No Overtaking", "meaning": "Overtaking prohibited", "detailed_explanation": "Do not overtake other vehicles in this area. Usually in dangerous curves, hills, or restricted zones."},
                    "am": {"name": "መቅደም አይፈቀድም", "meaning": "መቅደም የተከለከለ ነው", "detailed_explanation": "በዚህ አካባቢ ሌሎች ተሽከርካሪዎችን አትቅደሙ። ብዙውን ጊዜ በአደገኛ ኩርባዎች፣ ጉድጓዶች ወይም የተገደቡ አካባቢዎች ይገኛል።"},
                    "ti": {"name": "ምቕዳም ኣይፍቀድ", "meaning": "ምቕዳም ተኸልኪሉ ኣሎ", "detailed_explanation": "ኣብዚ ከባቢ ካልኦት መካይን ኣይቕደም። መብዛሕትኡ ግዜ ኣብ ሓደገኛ ቁርባታት፣ ጎቦታት ወይ ዝተዓጸወ ከባቢታት ይርከብ።"},
                    "or": {"name": "Daanfachuu Hin Dandeenye", "meaning": "Daanfachuu hin eeggamu", "detailed_explanation": "Naannoo kana keessatti gaarreen biraa hin daanfatin. Yeroo baay'ee cimdiilee hamtuu, gaarreen ykn naannoo harkifametti argama."}
                }
            },
            {
                "code": "NOPARK_003",
                "image": "road_signs/no_parking.png",
                "category": rs_cat_objs["REGULATORY"],
                "translations": {
                    "en": {"name": "No Parking", "meaning": "Parking prohibited", "detailed_explanation": "Do not park your vehicle in this area. Stopping temporarily for loading/unloading may be allowed unless otherwise specified."},
                    "am": {"name": "መቆም አይፈቀድም", "meaning": "መቆም (ፓርኪንግ) የተከለከለ ነው", "detailed_explanation": "በዚህ አካባቢ ተሽከርካሪዎን አታቆሙ። ለመጫን/ለመራገፍ ጊዜያዊ መቆም ካልተከለከለ በስተቀር ይፈቀዳል።"},
                    "ti": {"name": "ምቁጽጻር ኣይፍቀድ", "meaning": "ምቁጽጻር ተኸልኪሉ ኣሎ", "detailed_explanation": "ኣብዚ ከባቢ መካይኻ ኣይቁጽጾ። ንምጽዋት/ንምውራድ ንግዜኡ ምቁጽጻር ካብ ዘይተኸልከለ በቶም ይፍቀድ።"},
                    "or": {"name": "Baachuu Hin Dandeenye", "meaning": "Baachuu hin eeggamu", "detailed_explanation": "Naannoo kana keessatti gaarrii keessan hin baachinaa. Sochii guutuu/baasuuf yeroo gabaabaa dhaabuu yoo hin dhorgamin ni danda'ama."}
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
            #


        self.stdout.write(self.style.SUCCESS(
            f"Complete seeding finished successfully! "
            f"({len(question_objs)} questions, {len(exam_objs)} exams created)"
        ))