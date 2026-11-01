# Haq privacy policy

Last updated: 1 November 2026

Haq is an Android app that helps you write a complaint to get back money a company owes you.
This page says what happens to what you give it. Haq is built and run by one independent
developer (GitHub: Shukla070), who is responsible for your data.

## What Haq collects

- **What you tell it:** your account of what happened and your answers to its questions.
- **Your name**, which signs your complaint.
- **Files you choose to add:** screenshots, PDFs, text and voice notes. They can contain bank,
  order or payment details. Haq sees only the photos and files you pick or share with it.
- **A random device token** made by the app. The server keeps only a scrambled form (a hash) of
  it, and uses it to keep your cases yours.
- **The complaint and case record** Haq builds from these.

Haq has no accounts, ads or analytics. It does not ask for your phone number, contacts or
location. The microphone is used only while you record a voice note.

## Why

Only to work on your case: to read your proof, work out what the rules entitle you to, write
your complaint, and remind you of its dates. Your data is not sold.

## Who else receives it

- **Meta**, through the Meta Model API. Your files, voice notes, text and name are sent to Meta's
  AI models, which read and transcribe them and work on your case. Haq uses Meta's standard
  models, not the Contributor models whose input may be used for product improvement. Meta's API
  terms apply to what it receives.
- **Amazon Web Services**, which hosts the server, in Mumbai, India.
- **Anyone you send your complaint to.** Haq never sends anything itself. Your email app opens with
  the complaint and proof filled in, and you choose whether to send it.

## Sensitive numbers

Card numbers, Aadhaar numbers and OTPs are hidden from the text the agent works on, and a draft
containing one is refused. This has limits you should know:

- Screenshots, PDFs and voice notes are first sent to Meta's model to be read, so that model can
  see a number in them before it is hidden. If you can, cover such numbers before adding a file.
- Your original file is stored as you gave it. A file found to contain such a number is left out
  of the email Haq prepares, and the app tells you.
- Detection is automatic and can miss things. Never share a PIN, password or OTP.

## Damage photos

If your complaint is about a damaged item, Haq may send your photo to Meta's models to find the
damage, and save a marked copy with your case. The copy is added to the email Haq prepares, next to
your original. The mark is made by AI and can be wrong, so check it and remove the copy from your
email if it is.

## How long it is kept

Your case stays on the server until you delete it in the app, which removes the case and its
files from the server. A case with no activity for 180 days is deleted automatically, so it can
also disappear if you are waiting on something for longer than that. Uninstalling the app or
clearing its data does not delete your cases from the server, and you can no longer reach them
afterwards: delete them in the app first, or contact the developer before you do.

Case data is sent over an encrypted connection (https).

Haq's limit counters use your IP address in memory for a day. It is not written to storage.

## Your choices

You can see your case in the app, delete it at any time, refuse the notification and microphone
permissions, and ask questions or raise a complaint about your data through the contact below.

## Children

Haq is not meant for anyone under 18.

## Not legal advice

Haq helps you write a complaint. It is not a lawyer, and it can make mistakes, so read your
complaint before you send it.

## Contact

Open an issue at <https://github.com/Shukla070/Haq/issues>. Do not put case details in an issue,
because issues are public.

## Changes

If this policy changes, the new version will be published here with a new date.
