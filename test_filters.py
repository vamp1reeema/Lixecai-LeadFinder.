import unittest

from filters import find_keyword, lead_rejection_reason


IGNORE = ["казино", "ставки", "крипто", "розыгрыш", "подпишись", "реферал"]


class LeadFilterTests(unittest.TestCase):
    def test_accepts_short_website_request(self):
        text = "Создать сайт"
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_accepts_short_website_request_with_budget(self):
        text = "Нужен сайт, бюджет 20 000 рублей"
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_accepts_clear_website_order(self):
        text = "Заказ #123. Нужно создать сайт для небольшой студии, бюджет обсудим."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_accepts_bot_request(self):
        text = "Ищу разработчика, который сделает Telegram-бота для записи клиентов."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_accepts_tilda_landing_page(self):
        text = "Нужен лендинг на Tilda для нового проекта. Кто возьмётся?"
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_rejects_vacancy(self):
        text = "Ищем разработчика в команду. Опыт работы от 2 лет, полный день."
        self.assertEqual(lead_rejection_reason(text, IGNORE), "вакансия или поиск сотрудника")

    def test_rejects_roundup(self):
        text = "Подборка заказов для дизайнеров на этой неделе: смотрите все заказы."
        self.assertEqual(
            lead_rejection_reason(text, IGNORE),
            "подборка нескольких заказов, а не отдельная заявка",
        )

    def test_rejects_complex_mini_app(self):
        text = "Нужно разработать Telegram Mini App с личным кабинетом и оплатой."
        self.assertIn("слишком сложный проект", lead_rejection_reason(text, IGNORE))

    def test_rejects_promo(self):
        text = "Больше проектов в нашем боте, переходите и подписывайтесь."
        self.assertEqual(lead_rejection_reason(text, IGNORE), "реклама или агрегатор")

    def test_rejects_stop_word(self):
        text = "Заказ #777: создать сайт казино с оплатой и личным кабинетом."
        self.assertEqual(
            lead_rejection_reason(text, IGNORE), "стоп-слово: казино"
        )

    def test_rejects_message_without_buyer_intent(self):
        text = "Разработчик сайтов рассказывает о своём новом проекте и технологиях."
        self.assertEqual(
            lead_rejection_reason(text, IGNORE),
            "нет явного намерения заказать услугу",
        )

    def test_rejects_incidental_bot_mention_in_targetologist_post(self):
        text = (
            "\u200b #таргетолог Для русскоязычных мини-продуктов об AI ищут таргетолога Facebook Ads. "
            "Нужно тестировать связки на небольших бюджетах и масштабировать рекламу по CPA. "
            "Воронка ведёт через посадочную страницу и Telegram-бота, продукт стоит 990 ₽"
        )
        self.assertEqual(
            lead_rejection_reason(text, IGNORE),
            "нет явного намерения заказать услугу",
        )

    def test_rejects_clear_self_promotion(self):
        text = "Делаю сайты под ключ на Tilda, ищу новые проекты и клиентов."
        self.assertEqual(lead_rejection_reason(text, IGNORE), "самореклама исполнителя")

    def test_rejects_developer_service_offer(self):
        text = "Разрабатываю Telegram-ботов на заказ, возьму в работу новые проекты."
        self.assertEqual(lead_rejection_reason(text, IGNORE), "самореклама исполнителя")

    def test_accepts_customer_request_asking_for_portfolio(self):
        text = "Нужен сайт для студии. Пришлите портфолио и стоимость разработки."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_rejects_unrelated_targetologist_request_with_incidental_bot_mention(self):
        text = "Нужен таргетолог для рекламы AI-продукта. У нас уже есть лендинг и Telegram-бот."
        self.assertEqual(
            lead_rejection_reason(text, IGNORE),
            "нет явного намерения заказать услугу",
        )

    def test_rejects_incidental_website_and_bot_mentions(self):
        text = "Ищем специалиста по рекламе. В проекте уже используются сайт и Telegram-бот."
        self.assertEqual(
            lead_rejection_reason(text, IGNORE),
            "вакансия или поиск сотрудника",
        )

    def test_accepts_direct_bot_order_even_with_extra_context(self):
        text = "Нужен Telegram-бот для записи клиентов. Бюджет обсудим."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_keyword_detection_is_case_insensitive(self):
        self.assertEqual(find_keyword("НУЖЕН САЙТ для проекта", ["нужен сайт"]), "нужен сайт")

    def test_accepts_b2b_landing_with_crm_mentioned_as_context(self):
        text = "Срочный запрос: B2B-лендинг на Tilda, заявки будут передаваться в CRM вручную."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_rejects_explicit_crm_integration(self):
        text = "Нужно создать сайт и настроить интеграцию с CRM через API."
        self.assertIn("интеграция CRM/ERP", lead_rejection_reason(text, IGNORE))

    def test_rejects_explicit_1c_integration(self):
        text = "Нужно разработать сайт с синхронизацией каталога и остатков с 1С."
        self.assertIn("интеграция с 1С", lead_rejection_reason(text, IGNORE))

    def test_accepts_simple_internet_shop_without_advanced_features(self):
        text = "Заказ #901: создать простой сайт-каталог интернет-магазина, без корзины и онлайн-оплаты."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_rejects_bitrix_development_request(self):
        text = "Ищу веб-разработчика для сайта на 1С-Битрикс, редакция Бизнес."
        self.assertIn("1С/Битрикс", lead_rejection_reason(text, IGNORE))

    def test_accepts_bitrix_as_incidental_context(self):
        text = "Нужен простой лендинг для компании, у нас уже есть сайт на Битрикс."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_rejects_online_shop_with_checkout(self):
        text = "Нужен интернет-магазин с корзиной, онлайн-оплатой и эквайрингом."
        self.assertIn("интернет-магазин", lead_rejection_reason(text, IGNORE))

    def test_rejects_self_promotion_with_portfolio(self):
        text = "Делаю сайты на Tilda, моё портфолио и кейсы по ссылке."
        self.assertEqual(lead_rejection_reason(text, IGNORE), "самореклама исполнителя")

    def test_accepts_customer_request_for_turnkey_site(self):
        text = "Нужен сайт под ключ для небольшой кофейни, бюджет обсудим."
        self.assertIsNone(lead_rejection_reason(text, IGNORE))

    def test_rejects_freelancer_seeking_clients(self):
        text = "Веб-разработчик, свободен для новых проектов, ищу клиентов."
        self.assertEqual(lead_rejection_reason(text, IGNORE), "самореклама исполнителя")


if __name__ == "__main__":
    unittest.main()
