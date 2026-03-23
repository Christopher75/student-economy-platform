"""
Management command: seed_data
Populates the database with realistic Ugandan/East African university student data
for demonstration purposes.
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with realistic demo data for the Student Economy Platform'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true', help='Clear existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            self._clear_data()

        self.stdout.write('Seeding categories...')
        self._seed_categories()

        self.stdout.write('Seeding users...')
        users = self._seed_users()

        self.stdout.write('Seeding marketplace listings...')
        listings = self._seed_listings(users)

        self.stdout.write('Seeding skill offerings...')
        skills = self._seed_skills(users)

        self.stdout.write('Seeding bookings...')
        bookings = self._seed_bookings(users, skills)

        self.stdout.write('Seeding reviews...')
        self._seed_reviews(bookings)

        self.stdout.write('Seeding messages...')
        self._seed_messages(users, listings)

        self.stdout.write('Seeding notifications...')
        self._seed_notifications(users)

        from marketplace.models import Listing
        from skills.models import SkillOffering, SkillBooking, Review
        from messaging.models import Message
        self.stdout.write(self.style.SUCCESS(
            '\nSeed complete!'
            f'\n  Users: {User.objects.count()}'
            f'\n  Listings: {Listing.objects.count()}'
            f'\n  Skill Offerings: {SkillOffering.objects.count()}'
            f'\n  Bookings: {SkillBooking.objects.count()}'
            f'\n  Reviews: {Review.objects.count()}'
            f'\n  Messages: {Message.objects.count()}'
            '\n\n  Admin login: admin@studenteconomy.ug / admin1234'
            '\n  Student login (any): amara.nakato@cavendish.ac.ug / student1234'
        ))

    def _clear_data(self):
        from marketplace.models import Listing, Category, SavedListing, ListingReport, ListingPhoto
        from skills.models import SkillOffering, SkillCategory, SkillBooking, Review, SkillPortfolioItem
        from messaging.models import Conversation, Message
        from notifications.models import Notification
        Review.objects.all().delete()
        SkillBooking.objects.all().delete()
        SkillPortfolioItem.objects.all().delete()
        SkillOffering.objects.all().delete()
        SkillCategory.objects.all().delete()
        SavedListing.objects.all().delete()
        ListingReport.objects.all().delete()
        ListingPhoto.objects.all().delete()
        Listing.objects.all().delete()
        Category.objects.all().delete()
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        Notification.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()

    def _seed_categories(self):
        from marketplace.models import Category
        from skills.models import SkillCategory

        marketplace_cats = [
            ('Textbooks & Study Materials', 'textbooks', '📚', 1),
            ('Electronics & Gadgets', 'electronics', '💻', 2),
            ('Furniture & Appliances', 'furniture', '🛋️', 3),
            ('Clothing & Fashion', 'clothing', '👗', 4),
            ('Sports & Fitness', 'sports', '⚽', 5),
            ('Stationery & Art Supplies', 'stationery', '✏️', 6),
            ('Food & Kitchen', 'food-kitchen', '🍳', 7),
            ('Other', 'other', '📦', 8),
        ]

        for name, slug, icon, order in marketplace_cats:
            Category.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'order': order, 'description': f'{name} on campus'}
            )

        skill_cats = [
            ('Academic Tutoring', 'academic-tutoring', '🎓', 1),
            ('IT & Tech Support', 'it-tech', '💻', 2),
            ('Design & Creative', 'design-creative', '🎨', 3),
            ('Writing & Editing', 'writing-editing', '✍️', 4),
            ('Photography & Video', 'photography-video', '📸', 5),
            ('Music & Arts', 'music-arts', '🎵', 6),
            ('Languages & Translation', 'languages-translation', '🗣️', 7),
            ('Business & Admin', 'business-admin', '💼', 8),
            ('Fitness & Coaching', 'fitness-coaching', '🏃', 9),
            ('Other', 'other-skills', '🌟', 10),
        ]

        for name, slug, icon, order in skill_cats:
            SkillCategory.objects.get_or_create(
                slug=slug,
                defaults={'name': name, 'icon': icon, 'order': order, 'description': f'{name} services'}
            )

    def _seed_users(self):
        # Create admin
        admin, _ = User.objects.get_or_create(
            email='admin@studenteconomy.ug',
            defaults={
                'username': 'admin',
                'full_name': 'Platform Administrator',
                'student_id': 'ADMIN001',
                'university': 'Cavendish University Uganda',
                'course': 'Computer Science',
                'year_of_study': 4,
                'phone_number': '+256700000001',
                'is_staff': True,
                'is_superuser': True,
                'is_verified': True,
                'is_email_verified': True,
                'verification_status': 'approved',
                'bio': 'Platform administrator.',
            }
        )
        if _:
            admin.set_password('admin1234')
            admin.save()

        # Realistic Ugandan student data
        students_data = [
            {
                'email': 'amara.nakato@cavendish.ac.ug',
                'username': 'amara_nakato',
                'full_name': 'Amara Nakato',
                'student_id': 'CUU/BSC/2021/001',
                'university': 'Cavendish University Uganda',
                'course': 'Bachelor of Science in Computer Science',
                'year_of_study': 3,
                'phone_number': '+256701234567',
                'bio': 'CS student passionate about AI and machine learning. I sell used textbooks and offer Python tutoring.',
            },
            {
                'email': 'brian.omoding@mak.ac.ug',
                'username': 'brian_omoding',
                'full_name': 'Brian Omoding',
                'student_id': 'MAK/BCOM/2022/045',
                'university': 'Makerere University',
                'course': 'Bachelor of Commerce',
                'year_of_study': 2,
                'phone_number': '+256702345678',
                'bio': 'Commerce student. Good at accounting tutoring and business writing. Always looking for affordable textbooks.',
            },
            {
                'email': 'sarah.achieng@must.ac.ug',
                'username': 'sarah_achieng',
                'full_name': 'Sarah Achieng',
                'student_id': 'MUST/BIT/2020/078',
                'university': 'Mbarara University of Science and Technology',
                'course': 'Bachelor of Information Technology',
                'year_of_study': 4,
                'phone_number': '+256703456789',
                'bio': 'Final year IT student. Expert in graphic design and web development. Available for freelance projects.',
            },
            {
                'email': 'david.ssempala@iuea.ac.ug',
                'username': 'david_ssempala',
                'full_name': 'David Ssempala',
                'student_id': 'IUEA/BA/2021/112',
                'university': 'International University of East Africa',
                'course': 'Bachelor of Arts in Communication',
                'year_of_study': 3,
                'phone_number': '+256704567890',
                'bio': 'Media student. Photographer and videographer available for events and portraits.',
            },
            {
                'email': 'grace.akello@kcca.ac.ug',
                'username': 'grace_akello',
                'full_name': 'Grace Akello',
                'student_id': 'KCCA/BNUR/2022/034',
                'university': 'Kampala Capital City Authority University',
                'course': 'Bachelor of Nursing',
                'year_of_study': 2,
                'phone_number': '+256705678901',
                'bio': 'Nursing student. Good at Biology and Chemistry tutoring. Selling nursing textbooks from year 1.',
            },
            {
                'email': 'peter.okello@nkumba.ac.ug',
                'username': 'peter_okello',
                'full_name': 'Peter Okello',
                'student_id': 'NKU/BENG/2020/089',
                'university': 'Nkumba University',
                'course': 'Bachelor of Engineering',
                'year_of_study': 4,
                'phone_number': '+256706789012',
                'bio': 'Engineering student specialising in electronics. Offers laptop and gadget repair services on campus.',
            },
            {
                'email': 'fatima.namutebi@cavendish.ac.ug',
                'username': 'fatima_namutebi',
                'full_name': 'Fatima Namutebi',
                'student_id': 'CUU/BBA/2023/056',
                'university': 'Cavendish University Uganda',
                'course': 'Bachelor of Business Administration',
                'year_of_study': 1,
                'phone_number': '+256707890123',
                'bio': 'First year BBA student looking to connect with senior students. Can help with Swahili translation.',
            },
            {
                'email': 'kenneth.mwesigwa@mak.ac.ug',
                'username': 'kenneth_mwesigwa',
                'full_name': 'Kenneth Mwesigwa',
                'student_id': 'MAK/BLAW/2021/023',
                'university': 'Makerere University',
                'course': 'Bachelor of Laws',
                'year_of_study': 3,
                'phone_number': '+256708901234',
                'bio': 'Law student. Offers essay proofreading and academic writing assistance. Selling law textbooks.',
            },
        ]

        created_users = []
        for data in students_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    **data,
                    'is_verified': True,
                    'is_email_verified': True,
                    'verification_status': 'approved',
                    'last_seen': timezone.now() - timedelta(hours=random.randint(1, 72)),
                }
            )
            if created:
                user.set_password('student1234')
                user.save()
            created_users.append(user)

        return created_users

    def _seed_listings(self, users):
        from marketplace.models import Category, Listing

        listings_data = [
            {
                'title': 'Engineering Mathematics Textbook (Stroud)',
                'description': 'Stroud Engineering Mathematics 7th Edition. Perfect condition, minimal highlighting. Essential for Year 1 and 2 engineering students. I bought it new, used for one semester.',
                'category': 'textbooks',
                'condition': 'like_new',
                'price': 35000,
                'negotiable': True,
                'university': 'Nkumba University',
                'campus_location': 'Library Block Area',
                'seller_idx': 5,
                'is_featured': True,
            },
            {
                'title': 'HP Laptop 8GB RAM i5 (Light Use)',
                'description': 'HP 15s laptop. Intel Core i5 10th Gen, 8GB RAM, 256GB SSD. Running Windows 11. Battery holds 4+ hours. Small scuff on the back cover — doesn\'t affect performance. Selling because I upgraded.',
                'category': 'electronics',
                'condition': 'good',
                'price': 850000,
                'negotiable': True,
                'university': 'Cavendish University Uganda',
                'campus_location': 'Main Campus, Block B',
                'seller_idx': 0,
                'is_featured': True,
            },
            {
                'title': 'Principles of Management Textbook',
                'description': 'Robbins & Coulter - Management 14th Edition. Used for BBA Year 1 and 2 courses. Some pencil annotations (easily erased). Great condition overall.',
                'category': 'textbooks',
                'condition': 'good',
                'price': 25000,
                'negotiable': False,
                'university': 'Cavendish University Uganda',
                'campus_location': 'Block C Student Area',
                'seller_idx': 6,
                'is_featured': False,
            },
            {
                'title': 'Canon EOS 200D DSLR Camera',
                'description': 'Canon EOS 200D with 18-55mm kit lens. Only 3,200 shutter actuations. Comes with original box, 16GB SD card, extra battery, and carry bag. Perfect for photography students or anyone who needs quality photos.',
                'category': 'electronics',
                'condition': 'like_new',
                'price': 1200000,
                'negotiable': True,
                'university': 'International University of East Africa',
                'campus_location': 'Media Department, Ground Floor',
                'seller_idx': 3,
                'is_featured': True,
            },
            {
                'title': 'Single Hostel Mattress (Foam)',
                'description': 'Standard 3.5 x 6 foam mattress. Used for one academic year. Clean, no stains. Selling because I am moving out of campus hostel. Available for pickup from Katanga Halls.',
                'category': 'furniture',
                'condition': 'good',
                'price': 55000,
                'negotiable': True,
                'university': 'Makerere University',
                'campus_location': 'Katanga Halls Area',
                'seller_idx': 1,
                'is_featured': False,
            },
            {
                'title': 'University Uniform Shirts (3 pcs)',
                'description': 'Three light blue university uniform shirts. Sizes: 2 Medium, 1 Large. Worn for less than one semester. Excellent condition. Selling because sizes no longer fit.',
                'category': 'clothing',
                'condition': 'like_new',
                'price': 30000,
                'negotiable': True,
                'university': 'Cavendish University Uganda',
                'campus_location': 'Cavendish Campus',
                'seller_idx': 4,
                'is_featured': False,
            },
            {
                'title': 'Clinical Nursing Textbooks (Set of 4)',
                'description': 'Fundamental of Nursing (Potter & Perry), Medical Surgical Nursing, Pharmacology for Nursing Care, and Maternal-Child Nursing. All 4 books for this price. Ideal for Year 1 nursing students.',
                'category': 'textbooks',
                'condition': 'good',
                'price': 120000,
                'negotiable': True,
                'university': 'Kampala Capital City Authority University',
                'campus_location': 'Nursing Block',
                'seller_idx': 4,
                'is_featured': True,
            },
            {
                'title': 'Samsung Galaxy A32 (64GB)',
                'description': 'Samsung Galaxy A32, 64GB internal, 4GB RAM, 5000mAh battery. Running Android 12. No scratches on screen (kept in case). One tiny chip on the corner of the frame. Original charger included.',
                'category': 'electronics',
                'condition': 'good',
                'price': 380000,
                'negotiable': True,
                'university': 'Makerere University',
                'campus_location': 'Main Library Opposite',
                'seller_idx': 7,
                'is_featured': False,
            },
            {
                'title': 'Football (Adidas, Size 5)',
                'description': 'Adidas Tango football, size 5. Great for campus matches. Used about 10 times — still has good bounce and no cracks. Selling because I changed sports.',
                'category': 'sports',
                'condition': 'good',
                'price': 45000,
                'negotiable': False,
                'university': 'Nkumba University',
                'campus_location': 'Sports Field Vicinity',
                'seller_idx': 5,
                'is_featured': False,
            },
            {
                'title': 'Wacom Drawing Tablet (Bamboo)',
                'description': 'Wacom Bamboo CTL-472 drawing tablet. Used for graphic design coursework. Works perfectly with Adobe Illustrator, Photoshop, and GIMP. Comes with original pen and extra nibs.',
                'category': 'electronics',
                'condition': 'like_new',
                'price': 150000,
                'negotiable': True,
                'university': 'Mbarara University of Science and Technology',
                'campus_location': 'ICT Building',
                'seller_idx': 2,
                'is_featured': True,
            },
            {
                'title': 'Electric Kettle (Russell Hobbs)',
                'description': 'Russell Hobbs 1.7L electric kettle. Works perfectly. Selling because I am done with campus life. Great for making tea, noodles, and hot drinks in hostel.',
                'category': 'food-kitchen',
                'condition': 'good',
                'price': 28000,
                'negotiable': False,
                'university': 'Cavendish University Uganda',
                'campus_location': 'Block A Hostel',
                'seller_idx': 6,
                'is_featured': False,
            },
            {
                'title': 'A3 Sketchbooks (Pack of 2, Unused)',
                'description': 'Two A3 hardcover sketchbooks, 100 pages each. Bought for a design project that was cancelled. Still shrink-wrapped. Perfect for fine arts, architecture, or design students.',
                'category': 'stationery',
                'condition': 'new',
                'price': 18000,
                'negotiable': False,
                'university': 'International University of East Africa',
                'campus_location': 'Arts Block',
                'seller_idx': 3,
                'is_featured': False,
            },
            {
                'title': 'Law of Contract Textbook + Notes',
                'description': 'Cheshire, Fifoot and Furmston\'s Law of Contract 17th Edition, plus my detailed lecture notes from Professor Mugisha\'s classes (2022/23 academic year). Package deal for LLB Year 2 students.',
                'category': 'textbooks',
                'condition': 'good',
                'price': 55000,
                'negotiable': True,
                'university': 'Makerere University',
                'campus_location': 'Law Building',
                'seller_idx': 7,
                'is_featured': False,
            },
            {
                'title': 'Study Desk + Chair (Wooden)',
                'description': 'Solid wooden study desk (120cm x 60cm) plus matching chair with foam cushion. Small scratch on desk surface. Sturdy and perfect for hostel or off-campus apartment. Must collect from Wandegeya.',
                'category': 'furniture',
                'condition': 'fair',
                'price': 85000,
                'negotiable': True,
                'university': 'Makerere University',
                'campus_location': 'Wandegeya Near Campus',
                'seller_idx': 1,
                'is_featured': False,
            },
            {
                'title': 'Graphic Design Course USB Drive (Adobe Suite Tutorials)',
                'description': 'USB drive with over 40GB of Adobe Photoshop, Illustrator, and Premiere Pro tutorial videos. Includes project files. Ideal for design students learning on their own time.',
                'category': 'stationery',
                'condition': 'new',
                'price': 15000,
                'negotiable': False,
                'university': 'Mbarara University of Science and Technology',
                'campus_location': 'ICT Lab Area',
                'seller_idx': 2,
                'is_featured': False,
            },
        ]

        created_listings = []
        for data in listings_data:
            seller = users[data.pop('seller_idx')]
            category_slug = data.pop('category')
            from marketplace.models import Category
            category = Category.objects.get(slug=category_slug)

            listing, created = Listing.objects.get_or_create(
                title=data['title'],
                seller=seller,
                defaults={
                    **{k: v for k, v in data.items()},
                    'category': category,
                    'status': 'available',
                    'views_count': random.randint(5, 120),
                }
            )
            created_listings.append(listing)

        # Mark one as sold
        if created_listings:
            sold = created_listings[4]
            sold.status = 'sold'
            sold.save()

        # Add a few saved listings
        from marketplace.models import SavedListing
        for i, listing in enumerate(created_listings[:5]):
            saver = users[(i + 2) % len(users)]
            if saver != listing.seller:
                SavedListing.objects.get_or_create(user=saver, listing=listing)

        return created_listings

    def _seed_skills(self, users):
        from skills.models import SkillCategory, SkillOffering

        skills_data = [
            {
                'title': 'Python & Data Science Tutoring',
                'description': 'I offer one-on-one and small group tutoring in Python programming and introductory data science. Topics: Python basics, NumPy, Pandas, Matplotlib, scikit-learn. I have been coding in Python for 3 years and have tutored 12+ students.',
                'category': 'academic-tutoring',
                'delivery_method': 'both',
                'price_type': 'hourly',
                'price_min': 15000,
                'price_max': 25000,
                'estimated_duration': '1-2 hours per session',
                'availability': 'Weekdays after 4pm, Saturdays 9am-5pm',
                'university': 'Cavendish University Uganda',
                'is_featured': True,
                'provider_idx': 0,
            },
            {
                'title': 'Logo & Brand Identity Design',
                'description': 'Professional logo design and brand identity for student businesses, clubs, and personal projects. I use Adobe Illustrator and will deliver in all formats (AI, PDF, PNG, SVG). Portfolio available on request.',
                'category': 'design-creative',
                'delivery_method': 'online',
                'price_type': 'fixed',
                'price_min': 50000,
                'price_max': 150000,
                'estimated_duration': '3-5 business days',
                'availability': 'Available throughout the week, turn-around within 5 days',
                'university': 'Mbarara University of Science and Technology',
                'is_featured': True,
                'provider_idx': 2,
            },
            {
                'title': 'Laptop Repair & IT Troubleshooting',
                'description': 'Laptop screen replacement, keyboard repair, RAM/SSD upgrades, OS installation, virus removal, and general troubleshooting. I have been repairing computers since secondary school. Bring your laptop to campus and I\'ll diagnose it for free.',
                'category': 'it-tech',
                'delivery_method': 'in_person',
                'price_type': 'fixed',
                'price_min': 10000,
                'price_max': 80000,
                'estimated_duration': 'Same day for most repairs',
                'availability': 'Monday-Friday 12pm-6pm, Saturday by appointment',
                'university': 'Nkumba University',
                'is_featured': True,
                'provider_idx': 5,
            },
            {
                'title': 'Event & Portrait Photography',
                'description': 'Professional photography for graduation ceremonies, student events, society activities, and personal portraits. I shoot in RAW and deliver fully edited photos within 24 hours. Over 30 campus events covered.',
                'category': 'photography-video',
                'delivery_method': 'in_person',
                'price_type': 'fixed',
                'price_min': 80000,
                'price_max': 250000,
                'estimated_duration': 'Depends on event (2-8 hours)',
                'availability': 'Weekends and occasional weekdays',
                'university': 'International University of East Africa',
                'is_featured': True,
                'provider_idx': 3,
            },
            {
                'title': 'Academic Essay Writing & Proofreading',
                'description': 'I help students improve their essays, dissertations, and reports. I offer proofreading (grammar, style), structural review, and citation formatting (APA, Harvard, MLA). Law and business papers are my specialty.',
                'category': 'writing-editing',
                'delivery_method': 'online',
                'price_type': 'fixed',
                'price_min': 10000,
                'price_max': 50000,
                'estimated_duration': '1-3 days depending on length',
                'availability': 'Most days, respond within 2 hours',
                'university': 'Makerere University',
                'is_featured': False,
                'provider_idx': 7,
            },
            {
                'title': 'Accounting & Finance Tutoring',
                'description': 'Tutoring in Financial Accounting, Management Accounting, and Corporate Finance. I have achieved Distinction in all three modules. Available for exam prep, assignment help, and regular study sessions.',
                'category': 'academic-tutoring',
                'delivery_method': 'both',
                'price_type': 'hourly',
                'price_min': 12000,
                'price_max': 20000,
                'estimated_duration': '1-2 hours',
                'availability': 'Tuesdays, Thursdays evenings and Saturdays',
                'university': 'Makerere University',
                'is_featured': False,
                'provider_idx': 1,
            },
            {
                'title': 'Swahili Language Lessons',
                'description': 'Native Swahili speaker offering conversational and written Swahili lessons. Perfect for students learning Swahili for travel, business, or academic purposes. Patient and encouraging teaching style.',
                'category': 'languages-translation',
                'delivery_method': 'both',
                'price_type': 'hourly',
                'price_min': 10000,
                'price_max': 15000,
                'estimated_duration': '1 hour per session',
                'availability': 'Flexible, most afternoons',
                'university': 'Cavendish University Uganda',
                'is_featured': False,
                'provider_idx': 6,
            },
            {
                'title': 'Fitness Coaching & Workout Planning',
                'description': 'Certified fitness enthusiast offering personalised workout plans and in-person coaching sessions. Specialise in weight loss, muscle building, and general fitness for students with busy schedules. Campus gym sessions available.',
                'category': 'fitness-coaching',
                'delivery_method': 'in_person',
                'price_type': 'fixed',
                'price_min': 20000,
                'price_max': 50000,
                'estimated_duration': '1 hour per session',
                'availability': 'Mornings 6-8am and evenings 5-7pm',
                'university': 'Nkumba University',
                'is_featured': False,
                'provider_idx': 5,
            },
            {
                'title': 'Social Media Content Creation',
                'description': 'Create engaging content for Instagram, TikTok, Facebook, and Twitter. I handle graphic posts, short-form video editing, caption writing, and hashtag strategy. Perfect for student-run businesses and university clubs.',
                'category': 'design-creative',
                'delivery_method': 'online',
                'price_type': 'fixed',
                'price_min': 30000,
                'price_max': 100000,
                'estimated_duration': '1 week for a full package (10 posts)',
                'availability': 'Available throughout the week',
                'university': 'Mbarara University of Science and Technology',
                'is_featured': False,
                'provider_idx': 2,
            },
            {
                'title': 'Biology & Chemistry Tutoring (O & A Level)',
                'description': 'Experienced tutor helping university students who need to revise A-level concepts for medical science, pharmacy, or nursing entrance requirements. Also covers university-level cell biology and biochemistry.',
                'category': 'academic-tutoring',
                'delivery_method': 'in_person',
                'price_type': 'hourly',
                'price_min': 15000,
                'price_max': 20000,
                'estimated_duration': '1-2 hours',
                'availability': 'Weekday evenings after 5pm',
                'university': 'Kampala Capital City Authority University',
                'is_featured': False,
                'provider_idx': 4,
            },
        ]

        created_skills = []
        for data in skills_data:
            provider = users[data.pop('provider_idx')]
            category_slug = data.pop('category')
            category = SkillCategory.objects.get(slug=category_slug)

            skill, created = SkillOffering.objects.get_or_create(
                title=data['title'],
                provider=provider,
                defaults={
                    **{k: v for k, v in data.items()},
                    'category': category,
                    'status': 'active',
                    'views_count': random.randint(10, 200),
                }
            )
            created_skills.append(skill)

        return created_skills

    def _seed_bookings(self, users, skills):
        from skills.models import SkillBooking

        booking_configs = [
            # (skill_idx, client_idx, status, days_ago, notes, price)
            (0, 1, 'completed', 30, 'Need help with Python lists and functions for my Year 2 CS assignment.', 15000),
            (0, 4, 'completed', 20, 'Preparing for my data structures exam next week. Focus on sorting algorithms.', 25000),
            (1, 3, 'completed', 45, 'Need a logo for our university photography club "Lens Collective".', 80000),
            (2, 0, 'completed', 15, 'My laptop screen cracked. Need replacement and general checkup.', 60000),
            (3, 6, 'confirmed', 5, 'Photography for our BBA class graduation dinner on Saturday evening.', 150000),
            (4, 5, 'pending', 2, 'Need my 4000-word dissertation chapter proofread before submission.', 35000),
            (5, 6, 'completed', 60, 'Struggling with double-entry bookkeeping for my accounting assignment.', 12000),
            (6, 3, 'confirmed', 7, 'Need basic Swahili for a trip to Tanzania. Two sessions please.', 30000),
            (1, 4, 'cancelled', 10, 'Needed a poster for campus event but event was cancelled.', 0),
            (9, 2, 'pending', 1, 'Need help understanding cell biology for upcoming test.', 15000),
        ]

        created_bookings = []
        for skill_idx, client_idx, status, days_ago, notes, price in booking_configs:
            if skill_idx >= len(skills) or client_idx >= len(users):
                continue
            skill = skills[skill_idx]
            client = users[client_idx]
            provider = skill.provider

            if client == provider:
                continue

            booking, created = SkillBooking.objects.get_or_create(
                skill=skill,
                client=client,
                provider=provider,
                defaults={
                    'status': status,
                    'requested_date': date.today() - timedelta(days=days_ago - 2),
                    'notes': notes,
                    'price_agreed': price if price > 0 else None,
                }
            )
            if created and days_ago > 0:
                SkillBooking.objects.filter(pk=booking.pk).update(
                    created_at=timezone.now() - timedelta(days=days_ago)
                )
            created_bookings.append(booking)

        return created_bookings

    def _seed_reviews(self, bookings):
        from skills.models import Review

        review_data = [
            # (booking_idx, review_type, rating, comment)
            (0, 'client_to_provider', 5, 'Amara is an excellent Python tutor. Very patient and explains concepts clearly. My assignment grade improved significantly after just two sessions. Highly recommend!'),
            (0, 'provider_to_client', 5, 'Brian was a great student — came prepared with questions and was eager to learn. Happy to tutor him again.'),
            (1, 'client_to_provider', 5, 'Perfect exam prep session. Covered everything I needed for my data structures exam. Got a B+!'),
            (2, 'client_to_provider', 4, 'Sarah created a great logo for our club. Very professional and receptive to feedback. Delivered ahead of schedule.'),
            (3, 'client_to_provider', 5, 'Peter fixed my laptop screen same day and it looks brand new. Prices are very fair compared to shops in town. Will come back.'),
            (5, 'client_to_provider', 5, 'Brian\'s accounting tutoring is excellent. He has a gift for explaining complex concepts in simple terms.'),
            (6, 'client_to_provider', 4, 'Fatima is a wonderful Swahili teacher. Patient, encouraging, and her sessions are very structured. Learned a lot in two sessions.'),
        ]

        for booking_idx, review_type, rating, comment in review_data:
            if booking_idx >= len(bookings):
                continue
            booking = bookings[booking_idx]
            if booking.status != 'completed':
                continue

            if review_type == 'client_to_provider':
                reviewer = booking.client
                reviewee = booking.provider
            else:
                reviewer = booking.provider
                reviewee = booking.client

            Review.objects.get_or_create(
                booking=booking,
                reviewer=reviewer,
                defaults={
                    'reviewee': reviewee,
                    'skill': booking.skill,
                    'rating': rating,
                    'comment': comment,
                    'review_type': review_type,
                }
            )

    def _seed_messages(self, users, listings):
        from messaging.models import Conversation, Message

        conversations_data = [
            {
                'participants': (users[1], users[0]),
                'listing': listings[1] if len(listings) > 1 else None,
                'messages': [
                    (users[1], 'Hi Amara! Is the HP laptop still available?'),
                    (users[0], 'Yes it is! Are you interested? It\'s in great condition.'),
                    (users[1], 'Definitely! Can I come see it tomorrow at campus?'),
                    (users[0], 'Sure, I\'m available after 3pm near Block B. Does that work?'),
                    (users[1], 'Perfect! I\'ll be there at 3:30pm. Can you hold it for me?'),
                ],
            },
            {
                'participants': (users[4], users[4 % len(users)]),
                'listing': listings[6] if len(listings) > 6 else None,
                'messages': [
                    (users[2], 'Hello! I\'m interested in the nursing textbooks. Are all 4 available?'),
                    (users[4], 'Yes, all 4 are available! Are you a nursing student?'),
                    (users[2], 'I\'m in Year 1. These would be perfect for my course. Can you do 100,000?'),
                    (users[4], 'I can do 110,000 — the books are in really good condition.'),
                ],
            },
            {
                'participants': (users[3], users[2]),
                'listing': None,
                'messages': [
                    (users[3], 'Hi Sarah! I saw your logo design skill — I need a logo for a small campus business I\'m starting.'),
                    (users[2], 'Hi David! Tell me more about the business. What\'s the concept?'),
                    (users[3], 'It\'s a photo printing service for students. Think something clean and modern.'),
                    (users[2], 'That sounds great! I can definitely help. My rate is 50,000 for a basic logo package.'),
                    (users[3], 'Let\'s go with that. When can you start?'),
                    (users[2], 'I can start this weekend. Send me any references or colour preferences.'),
                ],
            },
        ]

        for conv_data in conversations_data:
            participants = conv_data['participants']
            if participants[0] == participants[1]:
                continue

            conv = Conversation.objects.create(
                listing=conv_data.get('listing'),
            )
            for p in participants:
                conv.participants.add(p)

            for sender, content in conv_data['messages']:
                msg = Message.objects.create(
                    conversation=conv,
                    sender=sender,
                    content=content,
                )
                conv.last_message_at = msg.created_at
            conv.save(update_fields=['last_message_at'])

    def _seed_notifications(self, users):
        from notifications.models import Notification

        notif_data = [
            (users[0], 'new_message', 'New message from Brian', 'Brian Omoding sent you a message about your HP Laptop listing.', '/messages/'),
            (users[0], 'booking_request', 'New booking request', 'Grace Akello has requested a Python tutoring session.', '/bookings/'),
            (users[2], 'booking_accepted', 'Booking confirmed!', 'Your logo design booking has been confirmed by Sarah Achieng.', '/bookings/'),
            (users[5], 'new_review', 'New review received', 'Amara Nakato left you a 5-star review for laptop repair.', '/accounts/dashboard/'),
            (users[1], 'item_sold', 'Mattress listing update', 'Your Single Hostel Mattress listing has been saved by 2 users.', '/marketplace/'),
            (users[3], 'booking_completed', 'Booking completed', 'Your photography booking for BBA graduation dinner is complete. Please leave a review!', '/bookings/'),
        ]

        for user, notif_type, title, message, url in notif_data:
            Notification.objects.get_or_create(
                user=user,
                title=title,
                defaults={
                    'notification_type': notif_type,
                    'message': message,
                    'action_url': url,
                    'is_read': random.choice([True, False]),
                }
            )
