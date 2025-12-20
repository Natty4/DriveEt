import uuid
import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from core.models import (
    Language,
    RoadSignCategory,
    RoadSignCategoryTranslation,
    RoadSign,
    RoadSignTranslation,
    Question,
    QuestionTranslation,
    AnswerChoice,
    AnswerChoiceTranslation,
    Explanation,
    ExplanationTranslation,
    UserProfile,
    PaymentMethod,
    PaymentMethodTranslation,
    ArticleCategory, Article,
    ExamQuestion, ExamSession,
    QuestionCategory, 
    QuestionCategoryTranslation,
    BundleDefinition,
)

class Command(BaseCommand):
    help = 'Seeds initial data: admin user, 6 road signs with categories, and 9 questions with translations and explanations.'

    def handle(self, *args, **options):
        languages = Language.values()
        self.stdout.write(self.style.SUCCESS('Starting seeding process...'))

        # Create admin user if not exists
        if not User.objects.filter(username='admin').exists():
            admin = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='password'
            )
            UserProfile.objects.create(
                user=admin
            )
            self.stdout.write(self.style.SUCCESS('Admin user created.'))

        # Create Question Categories
        question_categories_data = [
            {
                'code': 'SIGN',
                'order': 1,
                'names': {
                    'en': 'Road Signs',
                    'am': 'የመንገድ ምልክቶች',
                    'ti': 'ምልክታት መገዲ',
                    'or': 'Mallattoolee Karaa',
                },
                'descriptions': {
                    'en': 'Questions about identifying and understanding road signs.',
                    'am': 'የመንገድ ምልክቶችን መለየትና መረዳት የሚመለከቱ ጥያቄዎች።',
                    'ti': 'ብዛዕባ ምልክታት መገዲ ምፍላጥን ምርዳእን ዘለዉ ሕቶታት።',
                    'or': 'Gaaffii mallattoolee karaa beekuu fi hubachuu ilaalu.',
                }
            },
            {
                'code': 'RULES',
                'order': 2,
                'names': {
                    'en': 'Traffic Rules',
                    'am': 'የትራፊክ ህጎች',
                    'ti': 'ሕግታት ትራፊክ',
                    'or': 'Seera Traafikii',
                },
                'descriptions': {
                    'en': 'Rules of the road, right of way, speed limits, overtaking, etc.',
                    'am': 'የመንገድ ህጎች፣ ቅድሚያ መስጠት፣ የፍጥነት ገደቦች፣ ማለፍ ወዘተ።',
                    'ti': 'ሕግታት መገዲ፣ ቅድሚያ ሃብ፣ ገደብ ፍጥነት፣ ምብጻሕን ወዘተ።',
                    'or': 'Seera karaa, mirga karaa kennuu, eenyummaa ariifannaa, ce’uu, etc.',
                }
            },
            {
                'code': 'VEHICLE',
                'order': 3,
                'names': {
                    'en': 'Vehicle Handling & Safety',
                    'am': 'ተሽከርካሪ አያያዝና ደህንነት',
                    'ti': 'ኣመራርሓ ተቀይዲን ደሓንነትን',
                    'or': 'Mootorra qabuu fi nageenya',
                },
                'descriptions': {
                    'en': 'Vehicle controls, maintenance checks, seatbelts, brakes, lights, etc.',
                    'am': 'የተሽከርካሪ መቆጣጠሪያዎች፣ ጥገና ፈተሻ፣ የደህንነት ቀበቶዎች፣ ብሬክ፣ መብራት ወዘተ።',
                    'ti': 'መቆጻጸሪ ተቀይዲ፣ ፈተሻ ጥገና፣ ቀበቶ ደሓንነት፣ ብሬክ፣ ብርሃንን ወዘተ።',
                    'or': 'Tapni mootorraa, barreessa qorannoo, ariifannaa nageenyaa, burreki, ibsaa, etc.',
                }
            },
            {
                'code': 'ETHICS',
                'order': 4,
                'names': {
                    'en': 'Driver Ethics & Responsibility',
                    'am': 'የሹፌር ስነምግባርና ኃላፊነት',
                    'ti': 'ስነምግባርን ሓላፍነትን ሹፌር',
                    'or': 'Aadaa fi ga’uumsa geejjibaa',
                },
                'descriptions': {
                    'en': 'Defensive driving, alcohol, fatigue, courtesy, responsibility.',
                    'am': 'ተከላካይ መንዳት፣ አልኮሆል፣ ድካም፣ ትህትና፣ ኃላፊነት።',
                    'ti': 'መንኩባኽብ ምንካይ፣ ኣልኮሆል፣ ሰተት፣ ምሕረት፣ ሓላፍነት።',
                    'or': 'Geejjibaa ittisa, alkoolii, dadhabina, obsaa, ga’uumsa.',
                }
            },
        ]

        categories = {}
        for cat_data in question_categories_data:
            category, created = QuestionCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults={'order': cat_data['order']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created category: {category.code}"))

            for lang in languages:
                QuestionCategoryTranslation.objects.update_or_create(
                    category=category,
                    language=lang,
                    defaults={
                        'name': cat_data['names'].get(lang, cat_data['names']['en']),
                        'description': cat_data['descriptions'].get(lang, cat_data['descriptions']['en']),
                    }
                )
            categories[cat_data['code']] = category
        
        
        # Create categories
        road_sign_categories_data = [
            {
                'code': 'WARNING',
                'order': 1,
                'names': {
                    'en': 'Warning',
                    'am': 'ማስጠንቀቂያ',
                    'ti': 'ምጥንቃቐ',
                    'or': 'Akeekkachiisa',
                },
                'descriptions': {
                    'en': 'Signs that warn of potential hazards.',
                    'am': 'ሊከሰቱ ስለሚችሉ አደጋዎች የሚያስጠነቅቁ ምልክቶች።',
                    'ti': 'ብዛዕባ ክመጽእ ዝኽእል ሓደጋታት ዜጠንቕቑ ምልክታት።',
                    'or': 'Mallattoolee balaa dhufuu malu akeekkachiisan.',
                }
            },
            {
                'code': 'REGULATORY',
                'order': 2,
                'names': {
                    'en': 'Regulatory',
                    'am': 'የቁጥጥር',
                    'ti': 'መቆጻጸሪ',
                    'or': 'To’annoo',
                },
                'descriptions': {
                    'en': 'Signs that must be obeyed.',
                    'am': 'መታዘዝ ያለባቸው ምልክቶች።',
                    'ti': 'ክእዘዙ ዘለዎም ምልክታት።',
                    'or': 'Mallattoolee hojii irra ooluu qaban.',
                }
            },
            {
                'code': 'INFORMATIVE',
                'order': 3,
                'names': {
                    'en': 'Informative',
                    'am': 'መረጃ ሰጪ',
                    'ti': 'መብርሂ',
                    'or': 'Odeeffannoo',
                },
                'descriptions': {
                    'en': 'Signs that provide information.',
                    'am': 'መረጃ የሚሰጡ ምልክቶች።',
                    'ti': 'ሓበሬታ ዚህቡ ምልክታት።',
                    'or': 'Mallattoolee odeeffannoo kennan.',
                }
            },
        ]

        sign_categories = {}
        for cat_data in road_sign_categories_data:
            cat, _ = RoadSignCategory.objects.get_or_create(
                code=cat_data['code'],
                defaults={'order': cat_data['order']}
            )
            sign_categories[cat_data['code']] = cat
            for lang in languages:
                RoadSignCategoryTranslation.objects.get_or_create(
                    category=cat,
                    language=lang,
                    defaults={
                        'name': cat_data['names'].get(lang, cat_data['names']['en']),
                        'description': cat_data['descriptions'].get(lang, cat_data['descriptions']['en']),
                    }
                )
        self.stdout.write(self.style.SUCCESS('Categories created.'))

        # Create 6 road signs
        signs_data = [
            {
                'code': 'STOP',
                'image': 'road_signs/stop.png',
                'category': 'REGULATORY',
                'names': {
                    'en': 'Stop Sign',
                    'am': 'የማቆሚያ ምልክት',
                    'ti': 'ምልክት ምቁራጽ',
                    'or': 'Mallattoo Dhaabbannaa',
                },
                'meanings': {
                    'en': 'Come to a complete stop.',
                    'am': 'ሙሉ በሙሉ ያቁሙ።',
                    'ti': 'ብምሉኡ ደው በል።',
                    'or': 'Guutummaatti dhaabbadhu.',
                },
                'explanations': {
                    'en': 'This octagonal red sign requires drivers to stop fully before proceeding.',
                    'am': 'ይህ ባለ ስምንት ጎን ቀይ ምልክት አሽከርካሪዎች ከመቀጠላቸው በፊት ሙሉ በሙሉ እንዲቆሙ ይጠይቃል።',
                    'ti': 'እዚ ሾሞንተ ኩርናዕ ዘለዎ ቀይሕ ምልክት ኣሽከርከርቲ ቅድሚ ምቕጻሎም ምሉእ ብምሉእ ደው ክብሉ ይድህብል።',
                    'or': 'Mallattoon diimaan koorniyaa saddeet qabu kun konkolaachiftoonni dura deemuu isaanii dura guutummaatti dhaabbachuu akka qaban hubachiisa.',
                }
            },
            {
                'code': 'YIELD',
                'image': 'road_signs/yield.png',
                'category': 'REGULATORY',
                'names': {
                    'en': 'Yield Sign',
                    'am': 'የምርምር/ቅድሚያ መስጫ ምልክት',
                    'ti': 'ምልክት ምፍናው/ምክፋት',
                    'or': 'Mallattoo Dabarsii/Kenni',
                },
                'meanings': {
                    'en': 'Give way to other traffic.',
                    'am': 'ለሌላው ትራፊክ ቅድሚያ ይስጡ።',
                    'ti': 'ንኻልእ ትራፊክ መገዲ ሃብ።',
                    'or': 'Karaa geejjibaa biroof kenni.',
                },
                'explanations': {
                    'en': 'Triangular sign indicating to slow down and yield.',
                    'am': 'እንዲቀንሱ እና ቅድሚያ እንዲሰጡ የሚያመለክት ባለሶስት ማዕዘን ምልክት።',
                    'ti': 'ምልክት ሰለስተ ኩርናዕ ዘለዎ ንቕልጥፍና ምቕናስን ምፍናውን ዘመልክት።',
                    'or': 'Mallattoo roggee sadii kan suuta deemuufi dabarsuuf agarsiisu.',
                }
            },
            {
                'code': 'SPEED_LIMIT_50',
                'image': 'road_signs/speed_limit_50.png',
                'category': 'REGULATORY',
                'names': {
                    'en': 'Speed Limit 50',
                    'am': 'የፍጥነት ገደብ 50',
                    'ti': 'ልዕሊ ፍጥነት 50',
                    'or': 'Daangaa Ariitii 50',
                },
                'meanings': {
                    'en': 'Maximum speed is 50 km/h.',
                    'am': 'ከፍተኛው ፍጥነት 50 ኪሜ/ሰዓት ነው።',
                    'ti': 'ብዝሑ ዝለዓለ ፍጥነት 50 ኪ.ሜ/ሰዓት እዩ።',
                    'or': 'Ariitiin ol’aanaa 50 km/h dha.',
                },
                'explanations': {
                    'en': 'Circular sign enforcing speed limit.',
                    'am': 'የፍጥነት ገደቡን የሚያስፈጽም ክብ ምልክት።',
                    'ti': 'ንፍጥነት ገደብ ዜጽንዕ ዙርያዊ ምልክት።',
                    'or': 'Mallattoo geengoo daangaa ariitii agarsiisu.',
                }
            },
            {
                'code': 'PEDESTRIAN_CROSSING',
                'image': 'road_signs/pedestrian_crossing.png',
                'category': 'WARNING',
                'names': {
                    'en': 'Pedestrian Crossing',
                    'am': 'የእግረኛ መሻገሪያ',
                    'ti': 'መተሓላለፊ እግረኛ',
                    'or': 'Ce’umsa Miilaa',
                },
                'meanings': {
                    'en': 'Pedestrians may be crossing.',
                    'am': 'እግረኞች ሊያቋርጡ ይችላሉ።',
                    'ti': 'እግረኛታት ክሳገሩ ይኽእሉ እዮም።',
                    'or': 'Namoonni miilaan deeman ce’uu malu.',
                },
                'explanations': {
                    'en': 'Yellow diamond sign warning of pedestrian area.',
                    'am': 'የእግረኛ አካባቢን የሚያስጠነቅቅ ቢጫ የአልማዝ ቅርጽ ያለው ምልክት።',
                    'ti': 'ብጫ አልማዝ ምልክት ንከባቢ እግረኛ ዜጠንቕቕ።',
                    'or': 'Mallattoo daaymondii keelloo naannoo ce’umsa miilaa akeekkachiisu.',
                }
            },
            {
                'code': 'NO_PARKING',
                'image': 'road_signs/no_parking.png',
                'category': 'REGULATORY',
                'names': {
                    'en': 'No Parking',
                    'am': 'ማቆም ክልክል ነው',
                    'ti': 'ደው ምባል ክልክል',
                    'or': 'Dhaabachuu Hin Hayyamamu',
                },
                'meanings': {
                    'en': 'Parking is prohibited.',
                    'am': 'ማቆም የተከለከለ ነው።',
                    'ti': 'ደው ምባል ክልክል እዩ።',
                    'or': 'Dhaabachuun dhoorkaadha.',
                },
                'explanations': {
                    'en': 'Blue circle with red slash indicating no parking.',
                    'am': 'ማቆም ክልክል መሆኑን የሚያመለክት ሰማያዊ ክብ በቀይ ሰረዝ።',
                    'ti': 'ሰማያዊ ኮቦ ክብ ብቀይሕ ሰረዝ ደው ምባል ክልክል ምዃኑ ዜመልክት።',
                    'or': 'Geengoo cuquliisaa sarara diimaan Dhaabachuu Dhoorkaadha kan agarsiisu.',
                }
            },
            {
                'code': 'HOSPITAL_AHEAD',
                'image': 'road_signs/hospital_ahead.png',
                'category': 'INFORMATIVE',
                'names': {
                    'en': 'Hospital Ahead',
                    'am': 'ሆስፒታል በቅርብ ርቀት',
                    'ti': 'ሆስፒታል ቀዳምነት',
                    'or': 'Hospitaalli Dura Jira',
                },
                'meanings': {
                    'en': 'Hospital is nearby.',
                    'am': 'ሆስፒታል በቅርብ ይገኛል።',
                    'ti': 'ሆስፒታል ኣብ ጥቓ እዩ።',
                    'or': 'Hospitaalli dhihoo jira.',
                },
                'explanations': {
                    'en': 'Blue square sign informing of hospital location.',
                    'am': 'የሆስፒታልን ቦታ የሚያሳውቅ ሰማያዊ አራት ማዕዘን ምልክት።',
                    'ti': 'ሰማያዊ ዕርብዒት ምልክት ንቦታ ሆስፒታል ዜፍልጥ።',
                    'or': 'Mallattoo rogee afurii cuquliisaa bakka hospitaalaatti argamuu isaa ibsu.',
                }
            },
        ]

        signs = {}
        for sign_data in signs_data:
            sign, _ = RoadSign.objects.get_or_create(
                code=sign_data['code'],
                defaults={
                    'image': sign_data['image'],
                    'category': categories.get(sign_data['category']),
                }
            )
            signs[sign_data['code']] = sign
            for lang in languages:
                RoadSignTranslation.objects.get_or_create(
                    road_sign=sign,
                    language=lang,
                    defaults={
                        'name': sign_data['names'].get(lang, sign_data['names']['en']),
                        'meaning': sign_data['meanings'].get(lang, sign_data['meanings']['en']),
                        'detailed_explanation': sign_data['explanations'].get(lang, sign_data['explanations']['en']),
                    }
                )
        self.stdout.write(self.style.SUCCESS('Road signs created.'))

        # Create 9 questions (mix of IT and TI, distributed among signs)
        questions_data = [
            # Question 1: IT for STOP
            {
                'road_sign_context': 'STOP',
                'question_type': 'IT',
                'category_code': 'SIGN',
                'is_premium': False,
                'difficulty': 1,
                'contents': {
                    'en': 'What does this sign mean?',
                    'am': 'ይህ ምልክት ምን ማለት ነው?',
                    'ti': 'እዚ ምልክት እዚ እንታይ ማለት እዩ?',
                    'or': 'Mallattoon kun maal jechuudha?',
                },
                'choices': [
                    {'text': {'en': 'Come to a complete stop.', 'am': 'ሙሉ በሙሉ ያቁሙ።', 'ti': 'ብምሉኡ ደው በል።', 'or': 'Guutummaatti dhaabbadhu.'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'Give way to other traffic.', 'am': 'ለሌላው ትራፊክ ቅድሚያ ይስጡ።', 'ti': 'ንኻልእ ትራፊክ መገዲ ሃብ።', 'or': 'Karaa geejjibaa biroof kenni.'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'Maximum speed is 50 km/h.', 'am': 'ከፍተኛው ፍጥነት 50 ኪሜ/ሰዓት ነው።', 'ti': 'ብዝሑ ዝለዓለ ፍጥነት 50 ኪ.ሜ/ሰዓት እዩ።', 'or': 'Ariitiin ol’aanaa 50 km/h dha.'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'Parking is prohibited.', 'am': 'ማቆም የተከለከለ ነው።', 'ti': 'ደው ምባል ክልክል እዩ።', 'or': 'Dhaabachuun dhoorkaadha.'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'The stop sign requires a full stop to ensure safety at intersections.',
                    'am': 'የማቆሚያ ምልክቱ በመገናኛ መንገዶች ላይ ደህንነትን ለማረጋገጥ ሙሉ በሙሉ እንዲቆም ይጠይቃል።',
                    'ti': 'ምልክት ምቁራጽ ንደሓንነት ኣብ መጋጠሚ መገድታት ንምርግጋጽ ምሉእ ምቁራጽ ይሓትት።',
                    'or': 'Mallattoon dhaabbannaa nagaa karaa wal-qunnamtii irratti mirkaneessuuf guutummaatti dhaabbachuu gaafata.',
                }
            },
            # Question 2: TI for YIELD
            {
                'road_sign_context': 'YIELD',
                'question_type': 'TI',
                'category_code': 'SIGN',
                'is_premium': False,
                'difficulty': 1,
                'contents': {
                    'en': 'Which sign means "Give way to other traffic"?',
                    'am': 'የቱ ምልክት "ለሌላው ትራፊክ ቅድሚያ ይስጡ" ማለት ነው?',
                    'ti': 'ኣየናይ ምልክት "ንኻልእ ትራፊክ መገዲ ሃብ" ማለት እዩ?',
                    'or': 'Mallattoon kam "Karaa geejjibaa biroof kenni" jechuudha?',
                },
                'choices': [
                    {'road_sign_option': 'YIELD', 'is_correct': True, 'order': 1, 'text': None},
                    {'road_sign_option': 'STOP', 'is_correct': False, 'order': 2, 'text': None},
                    {'road_sign_option': 'SPEED_LIMIT_50', 'is_correct': False, 'order': 3, 'text': None},
                    {'road_sign_option': 'NO_PARKING', 'is_correct': False, 'order': 4, 'text': None},
                ],
                'explanation_details': {
                    'en': 'The yield sign is triangular and indicates to slow down and give way.',
                    'am': 'የምርምር ምልክቱ ባለሶስት ማዕዘን ሲሆን ፍጥነትን በመቀነስ ቅድሚያ እንዲሰጡ ያመለክታል።',
                    'ti': 'ምልክት ምፍናው ሰለስተ ኩርናዕ ዘለዎ ኮይኑ ንቕልጥፍና ምቕናስን መገዲ ምሃብን የረድእ።',
                    'or': 'Mallattoon Dabarsii roggee sadii yoo ta’u, suuta deemuufi karaa kennuu agarsiisa.',
                }
            },
            # Question 3: IT for SPEED_LIMIT_50
            {
                'road_sign_context': 'SPEED_LIMIT_50',
                'question_type': 'IT',
                'category_code': 'SIGN',
                'is_premium': False,
                'difficulty': 2,
                'contents': {
                    'en': 'What is the meaning of this sign?',
                    'am': 'የዚህ ምልክት ትርጉም ምንድን ነው?',
                    'ti': 'ትርጉም እዚ ምልክት እዚ እንታይ እዩ?',
                    'or': 'Hiikni mallattoo kanaa maalidha?',
                },
                'choices': [
                    {'text': {'en': 'Maximum speed is 50 km/h.', 'am': 'ከፍተኛው ፍጥነት 50 ኪሜ/ሰዓት ነው።', 'ti': 'ብዝሑ ዝለዓለ ፍጥነት 50 ኪ.ሜ/ሰዓት እዩ።', 'or': 'Ariitiin ol’aanaa 50 km/h dha.'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'Pedestrians may be crossing.', 'am': 'እግረኞች ሊያቋርጡ ይችላሉ።', 'ti': 'እግረኛታት ክሳገሩ ይኽእሉ እዮም።', 'or': 'Namoonni miilaan deeman ce’uu malu.'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'Hospital is nearby.', 'am': 'ሆስፒታል በቅርብ ይገኛል።', 'ti': 'ሆስፒታል ኣብ ጥቓ እዩ።', 'or': 'Hospitaalli dhihoo jira.'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'Give way to other traffic.', 'am': 'ለሌላው ትራፊክ ቅድሚያ ይስጡ።', 'ti': 'ንኻልእ ትራፊክ መገዲ ሃብ።', 'or': 'Karaa geejjibaa biroof kenni.'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'This sign enforces a maximum speed to maintain safety.',
                    'am': 'ይህ ምልክት ደህንነትን ለመጠበቅ ከፍተኛውን ፍጥነት ያስገድዳል።',
                    'ti': 'እዚ ምልክት እዚ ደሓንነት ንምሕላው ዝለዓለ ፍጥነት የጽንዕ።',
                    'or': 'Mallattoon kun nagaa eeguuf ariitii ol’aanaa ni dirqisiisa.',
                }
            },
            # Question 4: TI for PEDESTRIAN_CROSSING
            {
                'road_sign_context': 'PEDESTRIAN_CROSSING',
                'question_type': 'TI',
                'category_code': 'SIGN',
                'is_premium': True,
                'difficulty': 2,
                'contents': {
                    'en': 'Select the sign for "Pedestrians may be crossing."',
                    'am': '“እግረኞች ሊያቋርጡ ይችላሉ” የሚለውን ምልክት ይምረጡ።',
                    'ti': 'ምልክት "እግረኛታት ክሳገሩ ይኽእሉ እዮም" ዘርኢ ምረጽ።',
                    'or': 'Mallattoo "Namoonni miilaan deeman ce’uu malu" agarsiisu fili.',
                },
                'choices': [
                    {'road_sign_option': 'PEDESTRIAN_CROSSING', 'is_correct': True, 'order': 1, 'text': None},
                    {'road_sign_option': 'HOSPITAL_AHEAD', 'is_correct': False, 'order': 2, 'text': None},
                    {'road_sign_option': 'YIELD', 'is_correct': False, 'order': 3, 'text': None},
                    {'road_sign_option': 'STOP', 'is_correct': False, 'order': 4, 'text': None},
                ],
                'explanation_details': {
                    'en': 'This warning sign alerts drivers to watch for pedestrians.',
                    'am': 'ይህ የማስጠንቀቂያ ምልክት አሽከርካሪዎች ለእግረኞች ትኩረት እንዲሰጡ ያሳስባል።',
                    'ti': 'እዚ ምልክት መጠንቀቕታ ንኣሽከርከርቲ ንእግረኛታት ክጥንቀቑ የዘኻኽር።',
                    'or': 'Mallattoon akeekkachiisaa kun konkolaachiftoonni namoota miilaan deeman akka eegan akeekkachiisa.',
                }
            },
            # Question 5: IT for NO_PARKING
            {
                'road_sign_context': 'NO_PARKING',
                'question_type': 'IT',
                'category_code': 'SIGN',
                'is_premium': False,
                'difficulty': 1,
                'contents': {
                    'en': 'What does this sign indicate?',
                    'am': 'ይህ ምልክት ምን ያመለክታል?',
                    'ti': 'እዚ ምልክት እዚ እንታይ የረድእ?',
                    'or': 'Mallattoon kun maal agarsiisa?',
                },
                'choices': [
                    {'text': {'en': 'Parking is prohibited.', 'am': 'ማቆም የተከለከለ ነው።', 'ti': 'ደው ምባል ክልክል እዩ።', 'or': 'Dhaabachuun dhoorkaadha.'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'Hospital is nearby.', 'am': 'ሆስፒታል በቅርብ ይገኛል።', 'ti': 'ሆስፒታል ኣብ ጥቓ እዩ።', 'or': 'Hospitaalli dhihoo jira.'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'Come to a complete stop.', 'am': 'ሙሉ በሙሉ ያቁሙ።', 'ti': 'ብምሉኡ ደው በል።', 'or': 'Guutummaatti dhaabbadhu.'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'Pedestrians may be crossing.', 'am': 'እግረኞች ሊያቋርጡ ይችላሉ።', 'ti': 'እግረኛታት ክሳገሩ ይኽእሉ እዮም።', 'or': 'Namoonni miilaan deeman ce’uu malu.'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'This regulatory sign prevents parking to keep areas clear.',
                    'am': 'ይህ የቁጥጥር ምልክት አካባቢዎችን ንጹህ ለማድረግ ማቆምን ይከለክላል።',
                    'ti': 'እዚ ምልክት መቆጻጸሪ ንከባቢታት ጽሩይ ንምግባር ደው ምባል ይኽልክል።',
                    'or': 'Mallattoon to’annoo kun naannoo qulqulluu gochuuf dhaabachuu ni dhorka.',
                }
            },
            # Question 6: TI for HOSPITAL_AHEAD
            {
                'road_sign_context': 'HOSPITAL_AHEAD',
                'question_type': 'TI',
                'category_code': 'SIGN',
                'is_premium': False,
                'difficulty': 3,
                'contents': {
                    'en': 'Which sign indicates "Hospital is nearby"?',
                    'am': 'የቱ ምልክት "ሆስፒታል በቅርብ ይገኛል" የሚለውን ያመለክታል?',
                    'ti': 'ኣየናይ ምልክት "ሆስፒታል ኣብ ጥቓ እዩ" ዘርኢ?',
                    'or': 'Mallattoon kam "Hospitaalli dhihoo jira" agarsiisa?',
                },
                'choices': [
                    {'road_sign_option': 'HOSPITAL_AHEAD', 'is_correct': True, 'order': 1, 'text': None},
                    {'road_sign_option': 'PEDESTRIAN_CROSSING', 'is_correct': False, 'order': 2, 'text': None},
                    {'road_sign_option': 'SPEED_LIMIT_50', 'is_correct': False, 'order': 3, 'text': None},
                    {'road_sign_option': 'NO_PARKING', 'is_correct': False, 'order': 4, 'text': None},
                ],
                'explanation_details': {
                    'en': 'This informative sign helps drivers locate hospitals.',
                    'am': 'ይህ መረጃ ሰጪ ምልክት አሽከርካሪዎች ሆስፒታሎችን እንዲያገኙ ይረዳል።',
                    'ti': 'እዚ ምልክት መብርሂ ንኣሽከርከርቲ ሆስፒታል ክረኽቡ ይሕግዝ።',
                    'or': 'Mallattoon odeeffannoo kun konkolaachiftoonni hospitaalota akka argatan gargaara.',
                }
            },
            # Question 7: IT for PEDESTRIAN_CROSSING
            {
                'road_sign_context': 'PEDESTRIAN_CROSSING',
                'question_type': 'IT',
                'category_code': 'SIGN',
                'is_premium': True,
                'difficulty': 2,
                'contents': {
                    'en': 'Interpret this sign.',
                    'am': 'ይህን ምልክት ይተርጉሙ።',
                    'ti': 'እዚ ምልክት እዚ ተርጉም።',
                    'or': 'Mallattoo kana hiiki.',
                },
                'choices': [
                    {'text': {'en': 'Pedestrians may be crossing.', 'am': 'እግረኞች ሊያቋርጡ ይችላሉ።', 'ti': 'እግረኛታት ክሳገሩ ይኽእሉ እዮም።', 'or': 'Namoonni miilaan deeman ce’uu malu.'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'Maximum speed is 50 km/h.', 'am': 'ከፍተኛው ፍጥነት 50 ኪሜ/ሰዓት ነው።', 'ti': 'ብዝሑ ዝለዓለ ፍጥነት 50 ኪ.ሜ/ሰዓት እዩ።', 'or': 'Ariitiin ol’aanaa 50 km/h dha.'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'Give way to other traffic.', 'am': 'ለሌላው ትራፊክ ቅድሚያ ይስጡ።', 'ti': 'ንኻልእ ትራፊክ መገዲ ሃብ።', 'or': 'Karaa geejjibaa biroof kenni.'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'Hospital is nearby.', 'am': 'ሆስፒታል በቅርብ ይገኛል።', 'ti': 'ሆስፒታል ኣብ ጥቓ እዩ።', 'or': 'Hospitaalli dhihoo jira.'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'Detailed: Watch for pedestrians and reduce speed if necessary.',
                    'am': 'ዝርዝር፡ ለእግረኞች ትኩረት ይስጡ እና አስፈላጊ ከሆነ ፍጥነትዎን ይቀንሱ።',
                    'ti': 'ዝርዝር፡ ንእግረኛታት ተጠንቀቕ እሞ እንተድኣ ኣድላዪ ኮይኑ ፍጥነትካ ቅነስ።',
                    'or': 'Bal’inaan: Namoota miilaan deeman eegiitii yoo barbaachise ariitii kee hir’isi.',
                }
            },
            # Question 8: TI for STOP
            {
                'road_sign_context': 'STOP',
                'question_type': 'TI',
                'category_code': 'SIGN',
                'is_premium': False,
                'difficulty': 1,
                'contents': {
                    'en': 'Choose the sign for "Come to a complete stop."',
                    'am': '“ሙሉ በሙሉ ያቁሙ” የሚለውን ምልክት ይምረጡ።',
                    'ti': 'ምልክት "ብምሉኡ ደው በል" ዘርኢ ምረጽ።',
                    'or': 'Mallattoo "Guutummaatti dhaabbadhu" jedhu fili.',
                },
                'choices': [
                    {'road_sign_option': 'STOP', 'is_correct': True, 'order': 1, 'text': None},
                    {'road_sign_option': 'YIELD', 'is_correct': False, 'order': 2, 'text': None},
                    {'road_sign_option': 'NO_PARKING', 'is_correct': False, 'order': 3, 'text': None},
                    {'road_sign_option': 'HOSPITAL_AHEAD', 'is_correct': False, 'order': 4, 'text': None},
                ],
                'explanation_details': {
                    'en': 'The stop sign is crucial for preventing accidents at junctions.',
                    'am': 'የማቆሚያ ምልክቱ በመገናኛዎች ላይ አደጋዎችን ለመከላከል ወሳኝ ነው።',
                    'ti': 'ምልክት ምቁራጽ ኣብ መጋጠሚታት ሓደጋታት ንምክልኻል ወሳኒ እዩ።',
                    'or': 'Mallattoon dhaabbannaa balaa daandii wal-qunnamtii irratti ittisuuf murteessaadha.',
                }
            },
            # Question 9: IT for HOSPITAL_AHEAD
            {
                'road_sign_context': 'HOSPITAL_AHEAD',
                'question_type': 'IT',
                'category_code': 'SIGN',
                'is_premium': True,
                'difficulty': 3,
                'contents': {
                    'en': 'What is this sign telling you?',
                    'am': 'ይህ ምልክት ምን እየነገረዎት ነው?',
                    'ti': 'እዚ ምልክት እዚ እንታይ እዩ ዜነግረካ ዘሎ?',
                    'or': 'Mallattoon kun maal siif hima?',
                },
                'choices': [
                    {'text': {'en': 'Hospital is nearby.', 'am': 'ሆስፒታል በቅርብ ይገኛል።', 'ti': 'ሆስፒታል ኣብ ጥቓ እዩ።', 'or': 'Hospitaalli dhihoo jira.'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'Parking is prohibited.', 'am': 'ማቆም የተከለከለ ነው።', 'ti': 'ደው ምባል ክልክል እዩ።', 'or': 'Dhaabachuun dhoorkaadha.'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'Pedestrians may be crossing.', 'am': 'እግረኞች ሊያቋርጡ ይችላሉ።', 'ti': 'እግረኛታት ክሳገሩ ይኽእሉ እዮም።', 'or': 'Namoonni miilaan deeman ce’uu malu.'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'Maximum speed is 50 km/h.', 'am': 'ከፍተኛው ፍጥነት 50 ኪሜ/ሰዓት ነው።', 'ti': 'ብዝሑ ዝለዓለ ፍጥነት 50 ኪ.ሜ/ሰዓት እዩ።', 'or': 'Ariitiin ol’aanaa 50 km/h dha.'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'This sign is placed before hospitals to inform drivers in advance.',
                    'am': 'ይህ ምልክት አሽከርካሪዎችን አስቀድሞ ለማሳወቅ ከሆስፒታሎች በፊት ይቀመጣል።',
                    'ti': 'እዚ ምልክት እዚ ንኣሽከርከርቲ ቅድሚኡ ንምፍላጥ ኣብ ቅድሚ ሆስፒታላት ይሰፍር።',
                    'or': 'Mallattoon kun duraan dursitee konkolaachiftoota beeksisuuf hospitaalota dura kaa’ama.',
                }
            },
            # Question 10: TT for 
            {
                'road_sign_context': None,
                'question_type': 'TT',
                'category_code': 'RULES',
                'is_premium': False,
                'difficulty': 1,
                'contents': {
                    'en': 'What is the most important reason for wearing a seatbelt?',
                    'am': 'የደህንነት ቀበቶ መልበስ በጣም አስፈላጊ የሆነው ምክንያት ምንድን ነው?',
                    'ti': 'ቀበቶ ደሓንነት ምትእሳር እቲ ኣዝዩ ኣገዳሲ ምኽንያት እንታይ እዩ?',
                    'or': 'Sababaa ariifannaa ariifachuu sababa bu’uraa maalidha?',
                },
                'choices': [
                    {'text': {'en': 'To reduce the risk of injury or death in a crash', 'am': 'በአደጋ ጊዜ ጉዳት ወይም ሞት እንዳይደርስ ለመቀነስ', 'ti': 'ኣብ ሓደጋ ጉድኣት ወይ ሞት ንምንካይ', 'or': 'Balaa keessatti miidhaa ykn du’a dabaluu irraa ittisuuf'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'To avoid getting a fine', 'am': 'ቅጣት እንዳይቀጣ ለመጠበቅ', 'ti': 'ቅጽበት ክንቀጸ ንምኽልካል', 'or': 'Adabbii irraa baraaruuf'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'To make the vehicle more comfortable', 'am': 'ተሽከርካሪውን የበለጠ ምቹ ለማድረግ', 'ti': 'ተቀይዲ ተወሰኽቲ ምቹእ ንምግባር', 'or': 'Mootorra akkaan mi’aa taasisuuf'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'Because it is required only for long trips', 'am': 'ረጅም ጉዞ ብቻ ያስፈልጋል ስለሆነ', 'ti': 'ኣብ ነዊሕ ጉዕዝ ጥራይ የድልዮ ስለዝኾነ', 'or': 'Imala dheeraa qofaaf barbaachisa'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'Seatbelts significantly reduce the risk of serious injury or death by keeping occupants in place during a collision.',
                    'am': 'የደህንነት ቀበቶዎች በግጭት ጊዜ ተሳፋሪዎችን በቦታቸው በመጠበቅ ከባድ ጉዳት ወይም ሞት እንዳይደርስ በእጅጉ ይቀንሳሉ።',
                    'ti': 'ቀበቶ ደሓንነት ኣብ ግጭት ተሳፋሪት ኣብ ቦታኦም ብምጽናዕ ካብ ከቢድ ጉድኣት ወይ ሞት ብዙሕ ይንክዩ።',
                    'or': 'Ariifannaan balaa keessatti miidhaa hamaa ykn du’a irraa eeguun hedduu hir’isaa.',
                }
            },

            {
                'road_sign_context': None,
                'question_type': 'TT',
                'category_code': 'RULES',
                'is_premium': False,
                'difficulty': 2,
                'contents': {
                    'en': 'When should you use your vehicle horn?',
                    'am': 'የተሽከርካሪውን ቀንድ (ሆርን) መቼ መጠቀም አለብኝ?',
                    'ti': 'ሆርን ተቀይዲ መዓስ ክትጥቀም ይግባእ?',
                    'or': 'Bocuu mootorraa yoom gochuu qabda?',
                },
                'choices': [
                    {'text': {'en': 'Only to avoid an imminent danger or accident', 'am': 'ቀጥተኛ አደጋ ወይም አደጋን ለመከላከል ብቻ', 'ti': 'ናይ ቀረባ ሓደጋ ንምኽልካል ጥራይ', 'or': 'Balaa dhufaa qabu irraa ittisuuf qofa'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'To greet other drivers', 'am': 'ሌሎች ሹፌሮችን ለመሰላምታ', 'ti': 'ካልእ ሹፌራት ንምቕባል', 'or': 'Geejjibaa biroo salamachuu'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'When you are angry at another driver', 'am': 'ሌላ ሹፌር በቁጣ ሲያስቆጣ', 'ti': 'ሓደ ሹፌር ብቁጥዓ ምስ ተቖጥዐ', 'or': 'Geejjibaa biroo aaruuf'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'To hurry slow drivers ahead', 'am': 'ፊት ላሉት ቀርፋፋ ሹፌሮች ለማስቸኮል', 'ti': 'ኣብ ቅድሚ ዘለዉ ቀስ ብቀስ ሹፌራት ንምድፋፋዕ', 'or': 'Geejjibaa ariifataa duratti ariifachiisuuf'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'The horn should only be used as a warning device to prevent accidents, not for expressing emotions or impatience.',
                    'am': 'ሆርን እንደ ማስጠንቀቂያ መሣሪያ ብቻ አደጋን ለመከላከል መጠቀም አለበት፣ ስሜት ወይም ተጠንቀቅ ለማለት አይደለም።',
                    'ti': 'ሆርን ከም መሣሪያ ምጥንቃቐ ጥራይ ንምኽልካል ሓደጋ ክጥቀም ይግባእ፣ ንስምዒት ወይ ቅጽበት ኣይኮነን።',
                    'or': 'Bocuun balaa ittisuuf qofa gochuu qaba, ariifannaa ykn aarsaa ibsuuf miti.',
                }
            },

            {
                'road_sign_context': None,
                'question_type': 'TT',
                'category_code': 'RULES',
                'is_premium': False,
                'difficulty': 2,
                'contents': {
                    'en': 'What should you check before starting a long journey?',
                    'am': 'ረጅም ጉዞ ከመጀመርዎ በፊት ምን ማረጋገጥ አለብዎት?',
                    'ti': 'ናይ ነዊሕ ጉዕዞ ቅድሚ ምጅማርካ እንታይ ክትፈትሽ ይግባእ?',
                    'or': 'Imala dheeraa jalqabuuf dura maal barbaachisa?',
                },
                'choices': [
                    {'text': {'en': 'Tire pressure, fuel, oil, water, lights, and brakes', 'am': 'የጎማ ግፊት፣ ነዳጅ፣ ዘይት፣ ውሃ፣ መብራት እና ብሬክ', 'ti': 'ግፊት ጎማ፣ ነዳጅ፣ ዘይት፣ ማይ፣ ብርሃንን ብሬክን', 'or': 'Cabbii taayii, uumaa, oo’oo, bishaan, ibsaa fi burreki'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'Only the fuel level', 'am': 'የነዳጅ መጠን ብቻ', 'ti': 'ደረት ነዳጅ ጥራይ', 'or': 'Uumaa qofa'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'The radio and air conditioning', 'am': 'ሬዲዮውን እና አየር ማቀዝቀዣውን', 'ti': 'ሬድዮንን ኮንዲሽነርንን', 'or': 'Reediyoo fi eegee'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'The cleanliness of the windows', 'am': 'የመስታወቶች ንጽህና ብቻ', 'ti': 'ጽሬት መስታወት ጥራይ', 'or': 'Qulqullina fiixee qofa'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'A pre-journey vehicle check helps prevent breakdowns and ensures safety. Key items include tires, fluids, lights, and brakes.',
                    'am': 'ጉዞ ከመጀመር በፊት የተሽከርካሪ ምርመራ መከሰት የሚችሉ ብልሽቶችን ይከላከላል እና ደህንነትን ያረጋግጣል።',
                    'ti': 'ቅድሚ ጉዕዞ ፈተሻ ተቀይዲ ብልሽት ክኽልክልን ደሓንነት ክረጋግጽን ይሕግዝ።',
                    'or': 'Imala jalqabuuf dura mootorra barreessuu balaa irraa eega fi nagaa mirkaneessa.',
                }
            },

            {
                'road_sign_context': None,
                'question_type': 'TT',
                'category_code': 'RULES',
                'is_premium': False,
                'difficulty': 2,
                'contents': {
                    'en': 'What does defensive driving mean?',
                    'am': 'ተከላካይ መንዳት ማለት ምን ማለት ነው?',
                    'ti': 'መንኩባኽብ ምንካይ ማለት እዩ?',
                    'or': 'Geejjibaa ittisa biyyaa maal jechuudha?',
                },
                'choices': [
                    {'text': {'en': 'Driving in a way that prevents accidents despite the actions of others', 'am': 'የሌሎችን ተግባር ቢኖርም አደጋን የሚከላከል መንዳት', 'ti': 'ግብሪ ካልእ ሰባት መነኣእስ ሓደጋ ክኽልክል ዝኽእል ምንካይ', 'or': 'Hojii namoota biroo alaalchiin balaa ittisuun geejjibuu'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'Driving fast to reach the destination quickly', 'am': 'ፈጥኖ ለመድረስ በፍጥነት መንዳት', 'ti': 'ብቕልጡፍ ንምብጻሕ ብፍጥነት ምንካይ', 'or': 'Daddarbaa bakka bu’aatti ga’uuf'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'Always being the first to move at traffic lights', 'am': 'በትራፊክ መብራቶች ላይ ሁልጊዜ መጀመሪያ መንቀሳቀስ', 'ti': 'ኣብ ብርሃናት ትራፊክ ኩሉ ግዜ ቀዳማይ ምንቅስቓስ', 'or': 'Ibsa traafikii irratti yoomiyyuu dursee ka’uu'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'Ignoring traffic rules when no police are around', 'am': 'ፖሊስ ባይኖርበት ጊዜ የትራፊክ ህጎችን መተው', 'ti': 'ፖሊስ ኣብ ከይሃለወ ሕጊ ትራፊክ ምትውውያይ', 'or': 'Poolisii hin jirretti haala trafficii alaa darbaa'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'Defensive driving means being prepared for the mistakes of other road users and driving cautiously to avoid accidents.',
                    'am': 'ተከላካይ መንዳት የሌሎች ሹፌሮች ስህተት ቢኖርም አደጋን ለመከላከል በጥንቃቄ መንዳት ማለት ነው።',
                    'ti': 'መንኩባኽብ ምንካይ ጌጋታት ካልእ ተጠቀምቲ መገዲ ተዳሊኻ ብጥንቃቀ ምንካይ ማለት እዩ።',
                    'or': 'Geejjibaa ittisa biyyaa jechuun dogoggora namoota biroo qooda geejjibaa irratti argamuuf qophii ta’uu dha.',
                }
            },

            {
                'road_sign_context': None,
                'question_type': 'TT',
                'category_code': 'RULES',
                'is_premium': False,
                'difficulty': 1,
                'contents': {
                    'en': 'What is the function of the brake pedal?',
                    'am': 'የብሬክ ፔዳል ተግባር ምንድን ነው?',
                    'ti': 'ተግባር ፔዳል ብሬክ እንታይ እዩ?',
                    'or': 'Tapni burreki maal goota?',
                },
                'choices': [
                    {'text': {'en': 'To slow down or stop the vehicle', 'am': 'ተሽከርካሪውን ፍጥነት ለመቀነስ ወይም ለማቆም', 'ti': 'ተቀይዲ ፍጥነት ንምንካይ ወይ ንምቁራጽ', 'or': 'Mootorra ariifachuu ykn dhaabachuu'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'To increase the speed', 'am': 'ፍጥነት ለመጨመር', 'ti': 'ፍጥነት ንምውሳኽ', 'or': 'Ariifannaa dabaluuf'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'To change gears', 'am': 'ጊር ለመቀየር', 'ti': 'ጊር ንምቕያር', 'or': 'Giira jijjiiruuf'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'To turn on the lights', 'am': 'መብራት ለማብራት', 'ti': 'ብርሃን ንምብራት', 'or': 'Ibsa banuu'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'The brake pedal controls the braking system and is used to reduce speed or bring the vehicle to a complete stop.',
                    'am': 'የብሬክ ፔዳል የብሬክ ሲስተምን ይቆጣጠራል እና ፍጥነትን ለመቀነስ ወይም ተሽከርካሪውን ሙሉ በሙሉ ለማቆም ያገለግላል።',
                    'ti': 'ፔዳል ብሬክ ሲስተም ብሬክ ይመራርን ፍጥነት ንምንካይ ወይ ተቀይዲ ብምሉኡ ንምቁራጽ ይጥቀም።',
                    'or': 'Tapni burrekiin sisitama burrekiin ariifannaa hir’isuu ykn mootorra guutummaatti dhaabachuu goota.',
                }
            },

            {
                'road_sign_context': None,
                'question_type': 'TT',
                'category_code': 'RULES',
                'is_premium': False,
                'difficulty': 2,
                'contents': {
                    'en': 'Why should you not drink alcohol before driving?',
                    'am': 'ከመንዳት በፊት አልኮሆል ለምን መጠጣት የለበትም?',
                    'ti': 'ቅድሚ ምንካይ ኣልኮሆል ስለምንታይ ክትሰት የብልካን?',
                    'or': 'Sababiin yeroo geejjibuu duratti alkoolii hin dhuguun maalif?',
                },
                'choices': [
                    {'text': {'en': 'It impairs judgment, reaction time, and coordination', 'am': 'ፍርድን፣ ምላሽ ጊዜንና ቅንጅትን ይጎዳል', 'ti': 'ፍርድን ግዜ ምላሽን ምትእስሳርን ይጎድኦ', 'or': 'Madaallii, yeroo deebii fi walii galtee miidha'}, 'is_correct': True, 'order': 1, 'road_sign_option': None},
                    {'text': {'en': 'It makes you drive faster', 'am': 'ፈጥኖ እንዲነዱ ያደርጋል', 'ti': 'ብፍጥነት ክትንከይ የገብረካ', 'or': 'Daddarbaa geejjibuuf'}, 'is_correct': False, 'order': 2, 'road_sign_option': None},
                    {'text': {'en': 'It helps you stay awake longer', 'am': 'ረዘም ላለ ጊዜ ንቁ እንዲሆኑ ይረዳል', 'ti': 'ንነዊሕ ግዜ ተነቒቕካ ክትጸንሕ ይሕግዘካ', 'or': 'Yeroo dheeraaf duukkubuu irraa oolcha'}, 'is_correct': False, 'order': 3, 'road_sign_option': None},
                    {'text': {'en': 'It has no effect on driving', 'am': 'በመንዳት ላይ ምንም ተጽእኖ የለውም', 'ti': 'ኣብ ምንካይ ዘለዎ ተጽእኖ የቡን', 'or': 'Geejjibaa irratti homaa hin qabu'}, 'is_correct': False, 'order': 4, 'road_sign_option': None},
                ],
                'explanation_details': {
                    'en': 'Alcohol slows reaction time, reduces concentration, and impairs judgment — all critical for safe driving.',
                    'am': 'አልኮሆል የምላሽ ጊዜን ያዘገየዋል፣ ትኩረትን ይቀንሳል፣ ፍርድንም ይጎዳል — ይህ ሁሉ ለደህንነቱ የተጠበቀ መንዳት ወሳኝ ነው።',
                    'ti': 'ኣልኮሆል ግዜ ምላሽ የደውል፣ ትኩረት ይንክይ፣ ፍርድ ይጎድኦ — ኩሉ ንደሓንነቱ ዘለዎ ምንካይ ኣገዳሲ እዩ።',
                    'or': 'Alkooliin yeroo deebii dachaa, xiyyeeffannaa hir’isaa, madaallii miidha — hundi geejjibaa nagaa irratti barbaachisa.',
                }
            },
        
        ]

        for q_data in questions_data:
            question = Question.objects.create(
                id=uuid.uuid4(),
                road_sign_context=signs.get(q_data.get('road_sign_context')) if q_data.get('road_sign_context') else None,
                question_type=q_data['question_type'],
                category=categories[q_data['category_code']],  # e.g., 'SIGN', 'RULES'
                is_premium=q_data['is_premium'],
                difficulty=q_data['difficulty'],
            )
            for lang in languages:
                QuestionTranslation.objects.create(
                    question=question,
                    language=lang,
                    content=q_data['contents'].get(lang, q_data['contents']['en']),
                )

            # Create choices
            for choice_data in q_data['choices']:
                road_sign_option = signs.get(choice_data['road_sign_option']) if choice_data['road_sign_option'] else None
                choice = AnswerChoice.objects.create(
                    question=question,
                    road_sign_option=road_sign_option,
                    is_correct=choice_data['is_correct'],
                    order=choice_data['order'],
                )
                if choice_data['text']:
                    for lang in languages:
                        AnswerChoiceTranslation.objects.create(
                            answer_choice=choice,
                            language=lang,
                            text=choice_data['text'].get(lang, choice_data['text']['en']),
                        )

            # Create explanation
            explanation = Explanation.objects.create(
                question=question,
            )
            for lang in languages:
                ExplanationTranslation.objects.create(
                    explanation=explanation,
                    language=lang,
                    detail=q_data['explanation_details'].get(lang, q_data['explanation_details']['en']),
                )

        # self.stdout.write(self.style.SUCCESS('Questions and explanations created.'))
        self.stdout.write(self.style.SUCCESS("6 Road signs with 4-language support created"))
        
        payment_methods = [
            {
                "code": "TELEBIRR",
                "name": "Telebirr",
                "amount": "200.00",
                "order": 10,
                "account": {
                    "en": "0911 234 567",
                    "am": "0911 234 567",
                    "ti": "0911 234 567",
                    "or": "0911 234 567",
                },
                "instruction": {
                    "en": "Send exactly <strong>200 ETB</strong> to <strong>0911 234 567 (Telebirr)</strong> with your full name in the remark.",
                    "am": "በትክክል <strong>200 ብር</strong> ወደ <strong>0911 234 567 (ቴሌብር)</strong> በመልእክት ሙሉ ስምዎን ጨምሮ ይላኩ።",
                    "ti": "200 ብር ብትኽክል ናብ <strong>0911 234567 (ቴሌብር)</strong> ምሉእ ሽምኻ ጽሒፍካ ላኽ",
                    "or": "Dabalata <strong>200 ETB</strong> <strong>0911 234 567 (Telebirr)</strong> fakkaataa maqaa kee guutuu barreessi",
                },
            },
            {
                "code": "CBEBIRR",
                "name": "CBE Birr",
                "amount": "200.00",
                "order": 20,
                "account": {
                    "en": "1000123456789",
                    "am": "1000123456789",
                    "ti": "1000123456789",
                    "or": "1000123456789",
                },
                "instruction": {
                    "en": "Pay <strong>200 ETB</strong> via CBE Birr to account <strong>1000123456789</strong> and write your full name.",
                    "am": "በሲቢኢ ብር <strong>200 ብር</strong> ወደ አካውንት <strong>1000123456789</strong> ይክፈሉ እና ሙሉ ስምዎን ይጻፉ።",
                    "ti": "200 ብር ብCBE Birr ናብ ቁጽሪ ኣካው�ል <strong>1000123456789</strong> ኣተው፣ ሽምኻ ጽሑፍ",
                    "or": "200 ETB CBE Birr n <strong>1000123456789</strong> erguu maqaa kee guutuu barreessi",
                },
            },
            {
                "code": "AMOLE",
                "name": "Amole",
                "amount": "200.00",
                "order": 30,
                "account": {
                    "en": "*888*123456789#",
                    "am": "*888*123456789#",
                    "ti": "*888*123456789#",
                    "or": "*888*123456789#",
                },
                "instruction": {
                    "en": "Dial <strong>*888*123456789#</strong> and pay <strong>200 ETB</strong>. Use your full name as reference.",
                    "am": "<strong>*888*123456789#</strong> ይደውሉ እና <strong>200 ብ�</strong> ይክፈሉ። ሙሉ ስምዎን እንደ ማጣቀሻ ይጠቀሙ።",
                    "ti": "<strong>*888*123456789#</strong> ደውል፣ 200 ብር ኣፅንፈ፣ ሽምኻ ጽሑፍ",
                    "or": "<strong>*888*123456789#</strong> kaadii 200 ETB kaffalchi maqaa kee guutuu barreessi",
                },
            },
            {
                "code": "HELLOCASH",
                "name": "HelloCash (Awash Bank)",
                "amount": "200.00",
                "order": 40,
                "account": {
                    "en": "*888*0911123456#",
                    "am": "*888*0911123456#",
                    "ti": "*888*0911123456#",
                    "or": "*888*0911123456#",
                },
                "instruction": {
                    "en": "Use HelloCash → Send Money → <strong>0911123456</strong> → Amount <strong>200</strong> ETB → Remark: your full name.",
                    "am": "ሄሎኬሽ → ገንዘብ ላክ → <strong>0911123456</strong> → 200 ብር → ማሳሰቢያ፡ ሙሉ ስምዎ",
                    "ti": "ሄሎኬሽ → ገንዘብ ላኽ → <strong>0911123456</strong> → 200 ብር → መግለጺ፡ ሽምኻ",
                    "or": "HelloCash → Money Erguu → <strong>0911123456</strong> → 200 ETB → Maqaa kee guutuu barreessi",
                },
            },
        ]

        for pm_data in payment_methods:
            pm, _ = PaymentMethod.objects.get_or_create(
                code=pm_data["code"],
                defaults={
                    "name": pm_data["name"],
                    "amount": pm_data["amount"],
                    "order": pm_data["order"],
                    "is_active": True,
                },
            )
            for lang in languages:
                PaymentMethodTranslation.objects.update_or_create(
                    payment_method=pm,
                    language=lang,
                    defaults={
                        "account_details": pm_data["account"].get(lang, pm_data["account"]["en"]),
                        "instruction": pm_data["instruction"].get(lang, pm_data["instruction"]["en"]),
                    },
                )
        self.stdout.write(self.style.SUCCESS("Payment methods (Telebirr, CBE Birr, Amole, HelloCash) created with translations"))
        

        # Create 3 Bundle Definitions 
        bundles = [
            {
                "name": "Premium Lifetime",
                "code": "PREMIUM_LIFETIME",
                "description": "Unlimited access forever - Best value",
                "exam_quota": 0,  # unlimited
                "total_chat_quota": 0,  # unlimited
                "daily_chat_limit": 100,
                "search_quota": 0,  # unlimited
                "has_unlimited_road_sign_quiz": True,
                "validity_days": 36500,  # ~100 years
                "price_etb": Decimal("499.00"),
                "is_active": True,
                "order": 1,
                "recommended": True,
            },
            {
                "name": "1 Year Pro",
                "code": "PRO_1YEAR",
                "description": "Full access for 1 year with all features",
                "exam_quota": 200,
                "total_chat_quota": 2000,
                "daily_chat_limit": 30,
                "search_quota": 10000,
                "has_unlimited_road_sign_quiz": True,
                "validity_days": 365,
                "price_etb": Decimal("299.00"),
                "is_active": True,
                "order": 2,
            },
            {
                "name": "6 Months Standard",
                "code": "STANDARD_6MONTHS",
                "description": "Balanced access for serious learners",
                "exam_quota": 100,
                "total_chat_quota": 1000,
                "daily_chat_limit": 20,
                "search_quota": 5000,
                "has_unlimited_road_sign_quiz": True,
                "validity_days": 180,
                "price_etb": Decimal("199.00"),
                "is_active": True,
                "order": 3,
                "recommended": True,
            },
            {
                "name": "3 Months Basic",
                "code": "BASIC_3MONTHS",
                "description": "Essential features to get you started",
                "exam_quota": 50,
                "total_chat_quota": 500,
                "daily_chat_limit": 15,
                "search_quota": 2500,
                "has_unlimited_road_sign_quiz": True,
                "validity_days": 90,
                "price_etb": Decimal("149.00"),
                "is_active": True,
                "order": 4,
            },
            {
                "name": "1 Month Trial",
                "code": "TRIAL_1MONTH",
                "description": "Try all features for 1 month",
                "exam_quota": 20,
                "total_chat_quota": 100,
                "daily_chat_limit": 10,
                "search_quota": 1000,
                "has_unlimited_road_sign_quiz": True,
                "validity_days": 30,
                "price_etb": Decimal("99.00"),
                "is_active": True,
                "order": 5,
            },
            {
                "name": "Chat Pro Bundle",
                "code": "CHAT_PRO",
                "description": "Extra AI chat for personalized learning",
                "exam_quota": 30,
                "total_chat_quota": 5000,
                "daily_chat_limit": 50,
                "search_quota": 2000,
                "has_unlimited_road_sign_quiz": True,
                "validity_days": 180,
                "price_etb": Decimal("249.00"),
                "is_active": True,
                "order": 6,
            },
            {
                "name": "Exam Master Bundle",
                "code": "EXAM_MASTER",
                "description": "Unlimited exam practice",
                "exam_quota": 500,
                "total_chat_quota": 100,
                "daily_chat_limit": 5,
                "search_quota": 20000,
                "has_unlimited_road_sign_quiz": True,
                "validity_days": 180,
                "price_etb": Decimal("229.00"),
                "is_active": True,
                "order": 7,
            },
        ]

        for i, bundle_data in enumerate(bundles, 1):
            BundleDefinition.objects.update_or_create(
                code=bundle_data["code"],
                defaults={
                    "name": bundle_data["name"],
                    "description": bundle_data["description"],
                    "exam_quota": bundle_data["exam_quota"],
                    "total_chat_quota": bundle_data["total_chat_quota"],
                    "daily_chat_limit": bundle_data["daily_chat_limit"],
                    "search_quota": bundle_data["search_quota"],
                    "has_unlimited_road_sign_quiz": bundle_data["has_unlimited_road_sign_quiz"],
                    "validity_days": bundle_data["validity_days"],
                    "price_etb": bundle_data["price_etb"],
                    "is_active": bundle_data["is_active"],
                    "order": bundle_data.get("order", i),
                }
            )

        self.stdout.write(self.style.SUCCESS("Bundle definitions seeded"))

        # 5. Article Categories
        article_cats = [
            {"name": "Traffic Laws", "slug": "traffic-laws", "order": 1},
            {"name": "Road Safety Tips", "slug": "safety-tips", "order": 2},
            {"name": "License Process", "slug": "license-process", "order": 3},
        ]

        for cat in article_cats:
            ArticleCategory.objects.update_or_create(
                slug=cat["slug"],
                defaults={"name": cat["name"], "order": cat["order"], "is_active": True}
            )
        self.stdout.write(self.style.SUCCESS("Article categories seeded"))

        # 6. Sample Articles (Free + Premium)
        articles = [
            {
                "title": "Understanding Ethiopian Traffic Signs",
                "slug": "understanding-traffic-signs",
                "content": "<p>Traffic signs in Ethiopia are categorized into...</p><p>Warning signs are diamond-shaped...</p>",
                "category": "traffic-laws",
                "is_premium": False,
            },
            {
                "title": "How to Renew Your Driving License in Ethiopia",
                "slug": "renew-driving-license",
                "content": "<p>Renewing your license is straightforward...</p><p>Requirements include...</p>",
                "category": "license-process",
                "is_premium": False,
            },
            {
                "title": "Advanced Defensive Driving Techniques",
                "slug": "defensive-driving",
                "content": "<p>For experienced drivers, mastering defensive techniques...</p><p>Includes handling black ice, animal crossings...</p>",
                "category": "safety-tips",
                "is_premium": True,
            },
        ]

        traffic_cat = ArticleCategory.objects.get(slug="traffic-laws")
        safety_cat = ArticleCategory.objects.get(slug="safety-tips")
        license_cat = ArticleCategory.objects.get(slug="license-process")

        cat_map = {
            "traffic-laws": traffic_cat,
            "safety-tips": safety_cat,
            "license-process": license_cat,
        }

        for art in articles:
            Article.objects.update_or_create(
                slug=art["slug"],
                defaults={
                    "title": art["title"],
                    "content": art["content"],
                    "category": cat_map[art["category"]],
                    "is_premium": art["is_premium"],
                    "order": 0,
                }
            )
        self.stdout.write(self.style.SUCCESS("Sample articles seeded"))
        
        # 6. Create Test Users with Exam History
        test_users = [
            ("Abebe Kebede", True),   # Pro user
            ("Meron Tadesse", True),
            ("Yonas Alemayehu", False),  # Free user
            ("Fatuma Ahmed", False),
            ("Tesfaye Girma", True),
        ]

        all_questions = list(Question.objects.all())
        if not all_questions:
            self.stdout.write(self.style.WARNING("No questions found. Skipping exam seeding."))
        else:
            for username, is_pro in test_users:
                user, created = User.objects.get_or_create(username=username.lower().replace(" ", "_"))
                if created:
                    user.set_password("test123")
                    user.save()
                profile, _ = UserProfile.objects.update_or_create(
                    user=user,
                )

                # Seed 3–7 past exam sessions per user
                num_exams = random.randint(3, 7)
                for i in range(num_exams):
                    days_ago = random.randint(1, 60)
                    start_time = timezone.now() - timedelta(days=days_ago, minutes=random.randint(0, 1440))
                    duration_seconds = random.randint(1200, 1800)  # 20–30 minutes
                    end_time = start_time + timedelta(seconds=duration_seconds)

                    # Select 50 random questions
                    selected_qs = random.sample(all_questions, min(50, len(all_questions)))

                    # Simulate realistic performance
                    base_accuracy = random.uniform(0.65, 0.95)
                    correct_count = int(len(selected_qs) * base_accuracy)
                    correct_count = max(correct_count + random.randint(-5, 5), 0)
                    score = round((correct_count / len(selected_qs)) * 100, 1)
                    passed = score >= 80

                    exam = ExamSession.objects.create(
                        user=user,
                        start_time=start_time,
                        end_time=end_time,
                        status="completed" if passed or random.random() > 0.1 else "timed_out",
                        score=score,
                        time_taken=duration_seconds,
                        passed=passed,
                    )

                    # Create ExamQuestion records with answers
                    for order, q in enumerate(selected_qs, 1):
                        selected_choice = None
                        is_correct = False
                        if order <= correct_count or random.random() < base_accuracy:
                            # Pick correct answer
                            correct_choices = [c for c in q.choices.all() if c.is_correct]
                            if correct_choices:
                                selected_choice = random.choice(correct_choices)
                                is_correct = True
                        else:
                            # Pick wrong answer
                            wrong_choices = [c for c in q.choices.all() if not c.is_correct]
                            if wrong_choices:
                                selected_choice = random.choice(wrong_choices)

                        ExamQuestion.objects.create(
                            exam_session=exam,
                            question=q,
                            order=order,
                            selected_answer=selected_choice,
                            is_correct=is_correct,
                            time_spent=random.randint(15, 60),
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Seeded exam for {user.username}: {score}% ({'PASS' if passed else 'FAIL'}) on {start_time.date()}"
                        )
                    )

        self.stdout.write(self.style.SUCCESS("Seed data creation completed successfully!"))
      

























































# from django.core.management.base import BaseCommand
# from django.contrib.auth.models import User
# from core.models import (
#     RoadSign, RoadSignTranslation, 
#     Question, QuestionTranslation,
#     AnswerChoice, AnswerChoiceTranslation,
#     Explanation, ExplanationTranslation,
#     PaymentMethod, PaymentMethodTranslation,
#     UserProfile
# )


# class Command(BaseCommand):
#     help = 'Seed initial data for the driving exam app with translation tables'
    
#     def handle(self, *args, **options):
#         self.stdout.write('Seeding initial data with translation tables...')
        
#         # Create payment methods with translations
#         self.create_payment_methods()
        
#         # Create sample road signs and questions with translations
#         self.create_sample_content()
        
#         # Create admin user
#         self.create_admin_user()
        
#         self.stdout.write(self.style.SUCCESS('Successfully seeded data with translations!'))
    
#     def create_payment_methods(self):
#         """Create payment methods with translations"""
#         payment_methods_data = [
#             {
#                 'name': 'Telebirr',
#                 'code': 'TELEBIRR',
#                 'order': 1,
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'account_details': 'Account: 251912345678\nName: Road Sign Practice App',
#                         'instruction': '1. Open Telebirr App\n2. Select "Send Money"\n3. Enter account number: 251912345678\n4. Send 150 ETB\n5. Save the transaction reference number'
#                     },
#                     {
#                         'language': 'am',
#                         'account_details': 'አካውንት: 251912345678\nስም: የመንገድ ምልክት አፕ',
#                         'instruction': '1. ቴሌብር አፕ ይክፈቱ\n2. "ገንዘብ ላክ" ይምረጡ\n3. አካውንት ቁጥር ያስገቡ: 251912345678\n4. 150 ብር ይላኩ\n5. የግብይት ማጣቀሻ ቁጥር ያስቀምጡ'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'account_details': 'Akkaawwuntii: 251912345678\nMaqaa: Appii Qorannoo Mallattoa Karaa',
#                         'instruction': '1. Appii Telebirr banadi\n2. "Qarshii ergi" filadhu\n3. Lakkoofsa akkaawwuntii galchi: 251912345678\n4. 150 Birrii ergi\n5. Lakkoofsa waamichaa gatii marii'
#                     },
#                 ]
#             },
#             {
#                 'name': 'Bank of Abyssinia',
#                 'code': 'BOA',
#                 'order': 2,
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'account_details': 'Account: 1000123456789\nName: Road Sign Exam Co.\nBranch: Bole Branch',
#                         'instruction': '1. Use BoA mobile banking or visit any branch\n2. Transfer to account 1000123456789\n3. Amount: 150 ETB\n4. Include your name as reference\n5. Save transaction receipt'
#                     },
#                     {
#                         'language': 'am',
#                         'account_details': 'አካውንት: 1000123456789\nስም: የመንገድ ምልክት ፈተና ኮምፓኒ\nቅርንጫፍ: ቦሌ ቅርንጫፍ',
#                         'instruction': '1. ቦኤ ሞባይል ባንኪንግ ይጠቀሙ ወይም ማንኛውንም ቅርንጫፍ ይጎብኙ\n2. ወደ አካውንት 1000123456789 ያስተላልፉ\n3. መጠን: 150 ብር\n4. ስምዎን እንደ ማጣቀሻ ያካትቱ\n5. የግብይት ክፈያ ደብዳቤ ያስቀምጡ'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'account_details': 'Akkaawwuntii: 1000123456789\nMaqaa: Kampaanii Qorannoo Mallattoa Karaa\nQixxee: Qixxee Bolee',
#                         'instruction': '1. Baankii moobayilii BOA fayyadama ykn qixxeewwan hundaa seeni\n2. Akkaawwuntii 1000123456789 keessatti baafadhu\n3. Baayina: 150 Birrii\n4. Maqaa kee waamichaa taasisii\n5. Raasiitii gatii marii qabadhu'
#                     },
#                 ]
#             },
#             {
#                 'name': 'Dashen Bank',
#                 'code': 'DASHEN',
#                 'order': 3,
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'account_details': 'Account: 2000345678901\nName: Road Sign Practice Ltd.\nBranch: Megenagna Branch',
#                         'instruction': '1. Use Dashen mobile banking\n2. Deposit to account 2000345678901\n3. Amount: 150 ETB\n4. Use your phone number as reference\n5. Save transaction ID'
#                     },
#                     {
#                         'language': 'am',
#                         'account_details': 'አካውንት: 2000345678901\nስም: የመንገድ ምልክት አፕ ሊሚተድ\nቅርንጫፍ: መገናኛ ቅርንጫፍ',
#                         'instruction': '1. ዳሸን ሞባይል ባንኪንግ ይጠቀሙ\n2. ወደ አካውንት 2000345678901 ያስገቡ\n3. መጠን: 150 ብር\n4. የስልክ ቁጥርዎን እንደ ማጣቀሻ ይጠቀሙ\n5. የግብይት መታወቂያ ያስቀምጡ'
#                     },
#                 ]
#             },
#         ]
        
#         for method_data in payment_methods_data:
#             method, created = PaymentMethod.objects.update_or_create(
#                 code=method_data['code'],
#                 defaults={
#                     'name': method_data['name'],
#                     'is_active': True,
#                     'order': method_data['order'],
#                 }
#             )
            
#             # Clear existing translations
#             method.translations.all().delete()
            
#             # Create new translations
#             for translation_data in method_data['translations']:
#                 PaymentMethodTranslation.objects.create(
#                     payment_method=method,
#                     language=translation_data['language'],
#                     account_details=translation_data['account_details'],
#                     instruction=translation_data['instruction']
#                 )
            
#             status = 'Created' if created else 'Updated'
#             self.stdout.write(f'{status} payment method: {method.name} with {len(method_data["translations"])} translations')
    
#     def create_sample_content(self):
#         """Create sample road signs, questions, answers, and explanations with translations"""
        
#         # Sample road signs data
#         road_signs_data = [
#             {
#                 'code': 'STOP',
#                 'image_name': 'stop_sign.png',
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'name': 'Stop Sign',
#                         'description': 'A regulatory traffic sign that requires drivers to come to a complete stop before proceeding.'
#                     },
#                     {
#                         'language': 'am',
#                         'name': 'መቆም ምልክት',
#                         'description': 'አሽከርካሪዎች ከመቀጠላቸው በፊት ሙሉ በሙሉ እንዲቆሙ የሚያስገድድ የህግ የትራፊክ ምልክት።'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'name': 'Mallattoa Dhaabuu',
#                         'description': 'Mallattoa seeraa karaa kan konkolataa guutuu dhaabuu dhaabu dirqisiisu.'
#                     },
#                     {
#                         'language': 'ti',
#                         'name': 'ምልክት ምቁም',
#                         'description': 'ኣሽከርካርያን ቅድሚ ምቕጻሎም ምሉእ ብምሉእ ከም ዝቁሙ ዝገብር ሕጊ ዝኸውን ትራፊክ ምልክት።'
#                     },
#                 ]
#             },
#             {
#                 'code': 'YIELD',
#                 'image_name': 'yield_sign.png',
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'name': 'Yield Sign',
#                         'description': 'A traffic sign indicating that drivers must slow down and yield to traffic on the intersecting road.'
#                     },
#                     {
#                         'language': 'am',
#                         'name': 'አሳልፍ ምልክት',
#                         'description': 'አሽከርካሪዎች መቀነስ እና በተገናኘው መንገድ ላይ ለሚገኙ ተሽከርካሪዎች መተው እንዳለባቸው የሚያመለክት የትራፊክ ምልክት።'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'name': 'Mallattoa Dhiisi',
#                         'description': 'Mallattoa karaa kan konkolataa saffisuu fi gara karaa walitti dhufee irra jiru dhiisuu qabu agarsiisu.'
#                     },
#                 ]
#             },
#             {
#                 'code': 'NO_PARKING',
#                 'image_name': 'no_parking_sign.png',
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'name': 'No Parking Sign',
#                         'description': 'A traffic sign that indicates parking is prohibited in the area.'
#                     },
#                     {
#                         'language': 'am',
#                         'name': 'ማቆም አልተፈቀደም ምልክት',
#                         'description': 'በአካባቢው መኪና ማቆም እንደማይፈቀድ የሚያመለክት የትራፊክ ምልክት።'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'name': 'Mallattoa Kuusaa Dhabamsiisuu',
#                         'description': 'Mallattoa karaa kan naannichaa kuusaa dhabamsiisuu agarsiisu.'
#                     },
#                 ]
#             },
#         ]
        
#         # Create road signs with translations
#         road_signs = {}
#         for sign_data in road_signs_data:
#             sign, created = RoadSign.objects.update_or_create(
#                 code=sign_data['code'],
#                 defaults={}
#             )
            
#             # Clear existing translations
#             sign.translations.all().delete()
            
#             # Create translations
#             for translation_data in sign_data['translations']:
#                 RoadSignTranslation.objects.create(
#                     road_sign=sign,
#                     language=translation_data['language'],
#                     name=translation_data['name'],
#                     description=translation_data['description']
#                 )
            
#             road_signs[sign.code] = sign
#             status = 'Created' if created else 'Updated'
#             self.stdout.write(f'{status} road sign: {sign.code} with {len(sign_data["translations"])} translations')
        
#         # Sample questions data
#         questions_data = [
#             {
#                 'road_sign': 'STOP',
#                 'is_premium': False,
#                 'difficulty': 1,
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'content': 'What does a red octagonal sign with the word "STOP" mean?'
#                     },
#                     {
#                         'language': 'am',
#                         'content': '"STOP" የሚለው ቃል ያለው ቀይ ስምንት ጎን ያለው ምልክት ምን ማለት ነው?'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'content': 'Mallattoa oktaagonaalii diimaa jechi "STOP" qabu maal jechuu dha?'
#                     },
#                     {
#                         'language': 'ti',
#                         'content': '"STOP" ዝብል ቃል ዘለዎ ቀይሕ ሸሞንተ ጐድናት ዘለዎ ምልክት እንታይ ማለት እዩ?'
#                     },
#                 ],
#                 'answer_choices': [
#                     {
#                         'is_correct': True,
#                         'order': 1,
#                         'translations': [
#                             {'language': 'en', 'text': 'Come to a complete stop'},
#                             {'language': 'am', 'text': 'ሙሉ በሙሉ ቁም'},
#                             {'language': 'or_ET', 'text': 'Guutuu dhaabuu'},
#                             {'language': 'ti', 'text': 'ምሉእ ብምሉእ ቁም'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 2,
#                         'translations': [
#                             {'language': 'en', 'text': 'Slow down and proceed with caution'},
#                             {'language': 'am', 'text': 'ያምር እና በጥንቃቄ ቀጥል'},
#                             {'language': 'or_ET', 'text': 'Saffisiifi eeggachuun itti fufi'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 3,
#                         'translations': [
#                             {'language': 'en', 'text': 'Yield to oncoming traffic'},
#                             {'language': 'am', 'text': 'ለሚመጡ ተሽከርካሪዎች መንገድ ስጥ'},
#                             {'language': 'or_ET', 'text': 'Karaa garaa dhufuuf dhiisi'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 4,
#                         'translations': [
#                             {'language': 'en', 'text': 'No parking allowed'},
#                             {'language': 'am', 'text': 'ማቆም አይፈቀድም'},
#                             {'language': 'or_ET', 'text': 'Kuusaa hin eeyyamamu'},
#                         ]
#                     },
#                 ],
#                 'explanation': {
#                     'media_url': 'https://example.com/media/stop_sign_explanation.jpg',
#                     'media_type': 'image',
#                     'translations': [
#                         {
#                             'language': 'en',
#                             'detail': 'The stop sign is a regulatory traffic sign that requires vehicles to come to a complete stop before proceeding. It is usually red and octagonal in shape.'
#                         },
#                         {
#                             'language': 'am',
#                             'detail': 'መቆም ምልክት ተሽከርካሪዎች ከመቀጠላቸው በፊት ሙሉ በሙሉ እንዲቆሙ የሚያስገድድ የህግ የትራፊክ ምልክት ነው። አብዛኛው ጊዜ ቀይ እና ስምንት ጎን ያለው ቅርጽ አለው።'
#                         },
#                         {
#                             'language': 'or_ET',
#                             'detail': 'Mallattoa dhaabuun mallattoa seeraa karaa kan konkolataa guutuu dhaabuu dhaabu dirqisiisu. Yeroo baayyee diimaa fi qaama oktaagonaalii qaba.'
#                         },
#                     ]
#                 }
#             },
#             {
#                 'road_sign': 'STOP',
#                 'is_premium': True,
#                 'difficulty': 2,
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'content': 'How long should you remain stopped at a stop sign?'
#                     },
#                     {
#                         'language': 'am',
#                         'content': 'በመቆም ምልክት ላይ ለምን ያህል ጊዜ መቆም አለብዎት?'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'content': 'Hanga yeroo kamitti mallattoa dhaabuu irratti dhaabuu qabda?'
#                     },
#                 ],
#                 'answer_choices': [
#                     {
#                         'is_correct': False,
#                         'order': 1,
#                         'translations': [
#                             {'language': 'en', 'text': '1 second'},
#                             {'language': 'am', 'text': '1 ሰከንድ'},
#                             {'language': 'or_ET', 'text': 'Sekondii 1'},
#                         ]
#                     },
#                     {
#                         'is_correct': True,
#                         'order': 2,
#                         'translations': [
#                             {'language': 'en', 'text': 'Until it is safe to proceed'},
#                             {'language': 'am', 'text': 'በጥንቃቄ መቀጠል እስኪቻል ድረስ'},
#                             {'language': 'or_ET', 'text': 'Hanga itti fufuu nageenyaan ta\'uutti'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 3,
#                         'translations': [
#                             {'language': 'en', 'text': '3 seconds'},
#                             {'language': 'am', 'text': '3 ሰከንድ'},
#                             {'language': 'or_ET', 'text': 'Sekondii 3'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 4,
#                         'translations': [
#                             {'language': 'en', 'text': '5 seconds'},
#                             {'language': 'am', 'text': '5 ሰከንድ'},
#                             {'language': 'or_ET', 'text': 'Sekondii 5'},
#                         ]
#                     },
#                 ],
#                 'explanation': {
#                     'media_url': 'https://example.com/media/stop_duration.mp4',
#                     'media_type': 'video',
#                     'translations': [
#                         {
#                             'language': 'en',
#                             'detail': 'At a stop sign, you must come to a complete stop and remain stopped until it is safe to proceed. There is no specific time requirement; you must wait until you can safely enter the intersection or roadway.'
#                         },
#                         {
#                             'language': 'am',
#                             'detail': 'በመቆም ምልክት ላይ፣ ሙሉ በሙሉ መቆም እና በጥንቃቄ መቀጠል እስኪቻል ድረስ መቆም አለብዎት። የተወሰነ የጊዜ መስፈርት የለም፤ በአደጋ አለመጋፈጥ ወደ መገናኛው ወይም ወደ መንገዱ እስኪገቡ ድረስ መጠበቅ አለብዎት።'
#                         },
#                     ]
#                 }
#             },
#             {
#                 'road_sign': 'YIELD',
#                 'is_premium': False,
#                 'difficulty': 2,
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'content': 'What should you do when you see a yield sign?'
#                     },
#                     {
#                         'language': 'am',
#                         'content': 'አሳልፍ ምልክት ሲያዩ ምን ማድረግ አለብዎት?'
#                     },
#                     {
#                         'language': 'or_ET',
#                         'content': 'Mallattoa dhiisuu yeroo argitan maal gochuu qabda?'
#                     },
#                 ],
#                 'answer_choices': [
#                     {
#                         'is_correct': False,
#                         'order': 1,
#                         'translations': [
#                             {'language': 'en', 'text': 'Stop completely'},
#                             {'language': 'am', 'text': 'ሙሉ በሙሉ ቁም'},
#                             {'language': 'or_ET', 'text': 'Guutuu dhaabuu'},
#                         ]
#                     },
#                     {
#                         'is_correct': True,
#                         'order': 2,
#                         'translations': [
#                             {'language': 'en', 'text': 'Slow down and be prepared to stop if necessary'},
#                             {'language': 'am', 'text': 'ያምር እና አስፈላጊ ከሆነ ለመቆም ይዘጋጁ'},
#                             {'language': 'or_ET', 'text': 'Saffisiifi yoo barbaachisaa ta\'e dhaabuu qophaa\'i'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 3,
#                         'translations': [
#                             {'language': 'en', 'text': 'Speed up to clear the intersection quickly'},
#                             {'language': 'am', 'text': 'መገናኛውን በፍጥነት ለማሳለፍ ፍጥነት ያስጨምሩ'},
#                             {'language': 'or_ET', 'text': 'Walitti dhufeen ariifatti dhiisuuf saffisa oomishi'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 4,
#                         'translations': [
#                             {'language': 'en', 'text': 'Ignore the sign if no traffic is visible'},
#                             {'language': 'am', 'text': 'ተሽከርካሪ ካልታየ ምልክቱን ችላ ይበሉ'},
#                             {'language': 'or_ET', 'text': 'Yoo karaa hin argamne mallatticha daangessi'},
#                         ]
#                     },
#                 ],
#                 'explanation': {
#                     'media_url': None,
#                     'media_type': None,
#                     'translations': [
#                         {
#                             'language': 'en',
#                             'detail': 'A yield sign means you must slow down and yield the right-of-way to traffic in the intersection you are crossing or the road you are entering. If necessary, stop before entering the intersection.'
#                         },
#                         {
#                             'language': 'am',
#                             'detail': 'አሳልፍ ምልክት ማለት መቀነስ እና የመንገድ መብትን ለሚገናኙት መገናኛ ወይም ለሚገቡት መንገድ ላይ ለሚገኙ ተሽከርካሪዎች መስጠት አለብዎት ማለት ነው። አስፈላጊ ከሆነ፣ ወደ መገናኛው ከመግባትዎ በፊት ይቁሙ።'
#                         },
#                     ]
#                 }
#             },
#             {
#                 'road_sign': 'NO_PARKING',
#                 'is_premium': True,
#                 'difficulty': 3,
#                 'translations': [
#                     {
#                         'language': 'en',
#                         'content': 'When does a no parking sign typically apply?'
#                     },
#                     {
#                         'language': 'am',
#                         'content': 'ማቆም አልተፈቀደም ምልክት በተለምዶ መቼ ይፈፀማል?'
#                     },
#                 ],
#                 'answer_choices': [
#                     {
#                         'is_correct': False,
#                         'order': 1,
#                         'translations': [
#                             {'language': 'en', 'text': 'Only during nighttime hours'},
#                             {'language': 'am', 'text': 'በሌሊት ሰዓት ብቻ'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 2,
#                         'translations': [
#                             {'language': 'en', 'text': 'Only on weekends'},
#                             {'language': 'am', 'text': 'ቅዳሜ እና እሁድ ብቻ'},
#                         ]
#                     },
#                     {
#                         'is_correct': True,
#                         'order': 3,
#                         'translations': [
#                             {'language': 'en', 'text': 'At all times unless otherwise indicated'},
#                             {'language': 'am', 'text': 'ያለበለዚያ ካልተገለጸ በስተቀር በሁሉም ጊዜ'},
#                         ]
#                     },
#                     {
#                         'is_correct': False,
#                         'order': 4,
#                         'translations': [
#                             {'language': 'en', 'text': 'Only during business hours'},
#                             {'language': 'am', 'text': 'በስራ ሰዓት ብቻ'},
#                         ]
#                     },
#                 ],
#                 'explanation': {
#                     'media_url': 'https://example.com/media/no_parking_zone.gif',
#                     'media_type': 'gif',
#                     'translations': [
#                         {
#                             'language': 'en',
#                             'detail': 'A no parking sign typically applies at all times unless specific times are posted on the sign. Always check for additional information on the sign such as time restrictions, days of the week, or specific conditions.'
#                         },
#                         {
#                             'language': 'am',
#                             'detail': 'ማቆም አልተፈቀደም ምልክት በተለምዶ የተወሰኑ ጊዜዎች በምልክቱ ላይ ካልተገለጹ በስተቀር በሁሉም ጊዜ ይፈፀማል። ሁልጊዜ በምልክቱ ላይ ላሉ ተጨማሪ መረጃዎች እንደ የጊዜ ገደቦች፣ የሳምንት ቀናት ወይም የተወሰኑ ሁኔታዎች ይፈትሹ።'
#                         },
#                     ]
#                 }
#             },
#         ]
        
#         # Create questions with translations
#         question_count = 0
#         for q_data in questions_data:
#             road_sign = road_signs.get(q_data['road_sign'])
#             if not road_sign:
#                 self.stdout.write(self.style.WARNING(f'Road sign {q_data["road_sign"]} not found, skipping question'))
#                 continue
            
#             # Create question
#             question = Question.objects.create(
#                 road_sign=road_sign,
#                 is_premium=q_data['is_premium'],
#                 difficulty=q_data['difficulty']
#             )
            
#             # Create question translations
#             for translation_data in q_data['translations']:
#                 QuestionTranslation.objects.create(
#                     question=question,
#                     language=translation_data['language'],
#                     content=translation_data['content']
#                 )
            
#             # Create answer choices with translations
#             for choice_data in q_data['answer_choices']:
#                 answer_choice = AnswerChoice.objects.create(
#                     question=question,
#                     is_correct=choice_data['is_correct'],
#                     order=choice_data['order']
#                 )
                
#                 # Create answer choice translations
#                 for translation_data in choice_data['translations']:
#                     AnswerChoiceTranslation.objects.create(
#                         answer_choice=answer_choice,
#                         language=translation_data['language'],
#                         text=translation_data['text']
#                     )
            
#             # Create explanation with translations
#             explanation = Explanation.objects.create(
#                 question=question,
#                 media_url=q_data['explanation']['media_url'],
#                 media_type=q_data['explanation']['media_type']
#             )
            
#             # Create explanation translations
#             for translation_data in q_data['explanation']['translations']:
#                 ExplanationTranslation.objects.create(
#                     explanation=explanation,
#                     language=translation_data['language'],
#                     detail=translation_data['detail']
#                 )
            
#             question_count += 1
#             premium_status = 'Premium' if q_data['is_premium'] else 'Free'
#             self.stdout.write(f'Created {premium_status} question for {q_data["road_sign"]} sign with {len(q_data["translations"])} translations')
        
#         self.stdout.write(f'Created {question_count} questions total')
    
#     def create_admin_user(self):
#         """Create admin user and test users"""
#         # Create admin user
#         if not User.objects.filter(username='admin').exists():
#             admin_user = User.objects.create_superuser(
#                 username='admin',
#                 email='admin@road-exam.com',
#                 password='admin123'
#             )
#             UserProfile.objects.create(user=admin_user)
#             self.stdout.write('Created admin user (username: admin, password: admin123)')
        
#         # Create test users
#         test_users = [
#             {'username': 'test_free', 'email': 'free@example.com', 'password': 'test123', 'is_pro': False},
#             {'username': 'test_pro', 'email': 'pro@example.com', 'password': 'test123', 'is_pro': True},
#             {'username': 'driver1', 'email': 'driver1@example.com', 'password': 'driver123', 'is_pro': False},
#         ]
        
#         for user_data in test_users:
#             if not User.objects.filter(username=user_data['username']).exists():
#                 user = User.objects.create_user(
#                     username=user_data['username'],
#                     email=user_data['email'],
#                     password=user_data['password']
#                 )
#                 profile = UserProfile.objects.create(user=user)
#                 if user_data['is_pro']:
#                     from django.utils import timezone
#                     profile.is_pro_user = True
#                     profile.pro_since = timezone.now()
#                     profile.save()
                
#                 status = 'Pro' if user_data['is_pro'] else 'Free'
#                 self.stdout.write(f'Created {status} test user: {user_data["username"]} (password: {user_data["password"]})')
                
                
                