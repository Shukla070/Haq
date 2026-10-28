# Sample cases

Fictional test cases. Every name, bank, account and reference number is made up; the card
number is a standard test number. Run one from `server/`:

```bash
python -m haq new "$(cat ../samples/upi-failed-debit/story.txt)" ../samples/upi-failed-debit/bank_sms.txt ../samples/upi-failed-debit/upi_app_status.txt ../samples/upi-failed-debit/statement_extract.txt
```

| Case | What it tests |
|---|---|
| `upi-failed-debit` | A transfer to a person that failed but was debited, not reversed after 16 days, no complaint yet. Expected: a bank complaint citing the T+1 rule and the compensation owed. The statement's card number must be masked. |
