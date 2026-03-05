Family Keeper

An online app designed to make managing a family shared ecosystem easier.


Features to include:
* Google Calendar integration.
* AI Image -> list recognition (take a picture of a list, and turn it into a list.)
* Attach a picture to a list item.


So there's the concept of a family.    Each family has members, which are user-family relationships.    each family has zero or more lists, these can be todo lists, grocery lists, or other lists (Chores, etc.).   There's also a shared calendar option to display everyone in the family's calendars on the same screen at the same time.   lists can be permissioned.

THere's a system of roles in a family.     There's the role of 'parent' and 'child' wher eparents can create new lists and assign tasks on chore lists, and require photos for chores.    Family admin should be able to assign roles, and also rename the roles for a given Family.

Users can create a new family, or ask to join a family.   Families are private, only shared with a code.   All data in a family should be private to that family.

Primary use case is phones, so whatever we need to do (app, whatever)  also it would be nice ot test on apple screens and android screens, if there's a way to do that.  Do we need apps?   We would need apple and android versions.



TS and Next.js for the front end.   The backend I'm flexible between like fastapi python.     Targetting railyway deploy, and vercel.   postgresql and redis are data standards for a reason.   security should be robust by design.