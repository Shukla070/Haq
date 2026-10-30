import unittest

from haq import amounts


class EnglishTest(unittest.TestCase):
    def test_plain_english_amounts(self):
        self.assertEqual({"4500"}, amounts.spoken_amounts("four thousand five hundred rupees"))
        self.assertEqual({"1299"}, amounts.spoken_amounts("twelve hundred and ninety nine"))

    def test_lakh_and_mixed_digits(self):
        self.assertEqual({"120000"}, amounts.spoken_amounts("one lakh twenty thousand"))
        self.assertEqual({"4500"}, amounts.spoken_amounts("4 thousand 500"))
        self.assertEqual({"150000"}, amounts.spoken_amounts("1.5 lakh"))

    def test_hyphens_decimals_and_a_hundred(self):
        self.assertEqual({"25000"}, amounts.spoken_amounts("twenty-five thousand"))
        self.assertEqual({"4500"}, amounts.spoken_amounts("4.5 thousand"))
        self.assertEqual({"1500"}, amounts.spoken_amounts("15 hundred"))
        self.assertEqual({"100"}, amounts.spoken_amounts("a hundred"))
        self.assertEqual({"10000000"}, amounts.spoken_amounts("ek crore"))

    def test_case_and_punctuation_are_ignored(self):
        self.assertEqual({"4500"}, amounts.spoken_amounts("FOUR thousand, FIVE hundred rupees!"))


class HinglishTest(unittest.TestCase):
    def test_fractions(self):
        self.assertEqual({"4500"}, amounts.spoken_amounts("saadhe chaar hazaar rupaye"))
        self.assertEqual({"150"}, amounts.spoken_amounts("dedh sau"))
        self.assertEqual({"1750"}, amounts.spoken_amounts("paune do hazaar"))
        self.assertEqual({"125"}, amounts.spoken_amounts("sava sau"))
        self.assertEqual({"2500"}, amounts.spoken_amounts("dhai hazaar"))

    def test_hindi_numbers(self):
        self.assertEqual({"1299"}, amounts.spoken_amounts("barah sau ninyanve"))
        self.assertEqual({"50"}, amounts.spoken_amounts("pachaas rupaye"))
        self.assertEqual({"100"}, amounts.spoken_amounts("sau rupaye"))
        self.assertEqual({"45000"}, amounts.spoken_amounts("45 hazaar"))

    def test_two_amounts_in_one_sentence(self):
        text = "maine chaar hazaar paanch sau bheje aur bank ne teen sau kaate"
        self.assertEqual({"4500", "300"}, amounts.spoken_amounts(text))

    def test_a_date_in_the_sentence_is_ignored(self):
        text = "Maine 12 October ko four thousand five hundred rupees bheje"
        self.assertEqual({"4500"}, amounts.spoken_amounts(text))


class DevanagariTest(unittest.TestCase):
    def test_words_and_fractions(self):
        self.assertEqual({"4500"}, amounts.spoken_amounts("चार हज़ार पांच सौ रुपये"))
        self.assertEqual({"4500"}, amounts.spoken_amounts("साढ़े चार हज़ार"))

    def test_devanagari_digits_with_and_without_commas(self):
        self.assertEqual({"4500"}, amounts.spoken_amounts("४,५००"))
        self.assertEqual({"4500"}, amounts.spoken_amounts("४५००"))


class IgnoredTest(unittest.TestCase):
    def test_numbers_without_magnitude_or_currency_give_nothing(self):
        self.assertEqual(set(), amounts.spoken_amounts("teen din pehle"))
        self.assertEqual(set(), amounts.spoken_amounts("do baar try kiya"))
        self.assertEqual(set(), amounts.spoken_amounts("I called them twice"))
        self.assertEqual(set(), amounts.spoken_amounts("one day"))
        self.assertEqual(set(), amounts.spoken_amounts("12 October"))

    def test_digit_only_amounts_are_left_for_the_verifier(self):
        self.assertEqual(set(), amounts.spoken_amounts("Rs 4,500"))
        self.assertEqual(set(), amounts.spoken_amounts("Rs. 4500 debited"))

    def test_a_hindi_full_stop_does_not_hide_an_amount(self):
        self.assertEqual({"500"}, amounts.spoken_amounts("पांच सौ।"))
        self.assertEqual({"50"}, amounts.spoken_amounts("पचास रुपये।"))

    def test_paise_after_thousands_means_money(self):
        self.assertEqual({"4000"}, amounts.spoken_amounts("chaar hazaar paise kat gaye"))

    def test_paise_are_ignored(self):
        self.assertEqual({"5"}, amounts.spoken_amounts("paanch rupaye pachaas paise"))
        self.assertEqual(set(), amounts.spoken_amounts("pachaas paise"))


if __name__ == "__main__":
    unittest.main()
