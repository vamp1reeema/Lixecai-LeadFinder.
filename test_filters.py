import unittest

from filters import find_keyword, lead_rejection_reason


IGNORE = ["казино", "ставки", "крипто", "розыгрыш", "подпишись", "реферал"]


class LeadFilterTests(unittest.TestCase):
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

    def test_rejects_online_shop_with_checkout(self):
        text = "Нужен интернет-магазин с корзиной, онлайн-оплатой и эквайрингом."
        self.assertIn("интернет-магазин", lead_rejection_reason(text, IGNORE))


if __name__ == "__main__":
    unittest.main()
