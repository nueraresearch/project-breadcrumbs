# Post Office Data Request — Aggregate Route Volume

**Status:** Draft for sending. Not yet sent, and no agreement exists.  
**Related:** D-56, [`PRE_REGISTRATION_ANALYSIS_PLAN.md`](PRE_REGISTRATION_ANALYSIS_PLAN.md) §7.1, [`../data/DATA_MODEL.md`](../data/DATA_MODEL.md)

## 1. What is being requested

One number per day: **how many packages the postal routes serving the deployment area carried.**

Three acceptable forms, in order of preference:

1. Daily totals for the study window, by route or by area.
2. Weekly totals for the same period.
3. A station-estimated typical daily figure for the routes in question, if nothing finer can be released.

Daily is preferred because removals are dated, and the whole point is pairing a removal date with the volume of packages that were on porches that day.

**Optional, and only if the station offers it:** the number of package-theft complaints recorded for the same area and period. This is useful but secondary. Do not press for it, and do not make the request contingent on it.

## 2. What is explicitly not requested

- recipient names, addresses, or ZIP+4 detail;
- tracking numbers or individual delivery records;
- carrier names, schedules, or route assignments;
- anything that could describe a single household.

If a figure is small enough that it might describe one address, it is outside the scope and should not be supplied.

## 3. Request letter (template)

> [Date]
>
> [Station Manager name]
> United States Postal Service
> [Station address]
> Monte Vista, CO [ZIP]
>
> **Re: Request for aggregate delivery volume — community research study**
>
> Dear [Name],
>
> I am [name], [role] with Nuera Research and Developmental Laboratories. We are running a small, voluntary research study in Monte Vista on package theft, funded and operated locally.
>
> Over a 90-day period beginning [date], ten instrumented packages will be placed on volunteer porches in the [area / routes] area. When a package is removed, we record the date. What we cannot know is how ordinary that date was: whether the street was carrying a normal number of packages or an unusually heavy load.
>
> We would like to ask for **one aggregate number per day**: how many packages the routes serving that area carried. Weekly totals or a typical daily figure would also be useful if daily data cannot be released.
>
> We are **not** asking for any information about individual deliveries, recipients, addresses, tracking numbers, or carriers. We do not want anything that could describe a single household, and we will not ask for it later.
>
> What we will do with the figure: pair it with the number of study packages removed that day and report the two together as context — for example, "three study packages were removed on a day on which the routes carried 22 packages." We will not compute a theft rate from the two numbers, and the published report will say so explicitly.
>
> What we will not do: identify any person, share the data with law enforcement, use it commercially, or disclose it onward except as an aggregate figure in our published results.
>
> We are happy to sign a written agreement covering scope, handling, retention, and publication; a draft is enclosed. We are also happy to meet, and to narrow or reshape the request to whatever the station can provide without extra work.
>
> Thank you for considering it.
>
> Sincerely,
> [Name]
> [Role], Nuera Research and Developmental Laboratories
> [Phone] · [Email]

## 4. Written agreement — draft terms

A short agreement is better than a long one that nobody reads. These are the clauses that matter.

1. **Parties.** Nuera Research and Developmental Laboratories ("the Project") and [station / office] ("the Station"). The Station confirms it has authority to release the figures, or that approval has been obtained.
2. **Purpose.** The figures are supplied for descriptive research context only, in a study of package removal in Monte Vista.
3. **Data supplied.** Aggregate package counts per day, per week, or as a typical daily figure, for the routes or area described in Schedule A. Optionally, aggregate theft-complaint counts for the same area and period.
4. **Exclusions.** No recipient names, addresses, ZIP+4 detail, tracking numbers, individual delivery records, carrier identities, or route assignments.
5. **Permitted use.** Pairing the aggregate figure with the date of a study removal, and reporting the two together descriptively.
6. **Prohibited use.** The Project will not compute or publish a theft rate, prevalence estimate, or probability from the supplied figures; will not use them for enforcement, investigation, or identification of any person; will not sell or license them; and will not disclose them onward except as an aggregate figure within published research outputs.
7. **No re-identification.** The Project will not attempt to link the figures to any individual, household, or address, and will not combine them with any other dataset for that purpose.
8. **Publication.** Only aggregate values appear in published outputs. Any figure that could describe a single household is suppressed. The Project will provide the Station with a copy of the aggregate results at least 14 days before publication and will correct factual errors the Station identifies.
9. **Security.** Figures are held in the Project's restricted dataset, accessible to named personnel only, and kept separate from participant and event records apart from a date join.
10. **Retention.** Figures are retained for 24 months after the final report, then destroyed, except for published aggregates.
11. **No warranty.** Figures are supplied as available, without guarantee of accuracy or completeness, and the Station is not liable for decisions taken from them.
12. **No cost.** No fee is payable by either party.
13. **Term and termination.** The agreement covers the study window and the analysis period, and either party may end it on 14 days' written notice. On termination, unpublished figures are destroyed on request.
14. **Governing law.** Colorado.

**Schedule A** records the routes or area covered, the granularity supplied, and the start and end dates. It should be filled in with the Station, not for it.

## 5. Why this may be declined

Worth knowing before the conversation, so a refusal is not read as obstruction:

- **Authority.** A station manager may not be able to release route-level volume without approval from above. Ask who can, rather than assuming the answer is no.
- **Commercial sensitivity.** Route volume is operational information, and USPS treats some of it as commercially sensitive.
- **Federal records rules.** USPS records may fall under a formal request process rather than a local agreement. If the station says "you'll need to request that properly", ask what process they mean and follow it.
- **Small numbers.** On a light route, a daily count can come close to describing individual addresses, which is a reason to accept weekly figures rather than push for daily.

**If it is declined**, the study proceeds without it. The pre-registration plan already treats the volume figures as context rather than a dependency, so their absence costs interpretation, not validity. The report says the context was unavailable, and why.

Do not substitute a guess, a national average, or a figure from another year. An invented denominator is worse than a missing one.

## 6. Internal handling

- Store figures in the delivery-volume context table defined in [`../data/DATA_MODEL.md`](../data/DATA_MODEL.md), joined by date only.
- Never merge them into participant or event records.
- Report them as: "removals occurred on a day on which the routes carried N packages", with the granularity stated.
- If the Station asks for the study's aggregate results in return, that is a reasonable request and should be honoured; it costs nothing and it is the honest trade.
