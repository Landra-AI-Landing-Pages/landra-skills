# Audience research

This is the part of the work that compounds. A page written from a real reader beats a page written from a category. Research is expensive to produce and worthless if it evaporates when the conversation ends, which is what `save_brand_research` is for.

**Always read before you research.** Call `get_brand_research` first. If a dossier already exists, build on it rather than starting over, and refresh individual avatars by reusing their id.

## Where to actually look

Do real research. Web search, real sources, real quotes. In rough order of value:

1. **The brand's own reviews.** Their site, their Shopify reviews, their Amazon listing. This is the highest-signal source because it is the actual buyer of the actual product. Read the 3-star reviews hardest: 5-star reviews tell you what people say, 3-star reviews tell you what nearly stopped them.
2. **Competitor reviews, especially the bad ones.** A competitor's 1- and 2-star reviews are a list of unmet needs in the category, written by people who already tried to buy. That is where objections come from.
3. **Forums and communities.** Reddit, category-specific forums, Facebook groups. This is where people use their own words with no brand watching, which is where voice-of-customer language comes from.
4. **Competitor landing pages and ads.** What claims does the category lean on, what does everyone say, and therefore what does nobody say. Useful for finding the angle nobody is running.
5. **The brand's own site.** Useful for facts, weak for audience. Landra already analyzed it. Do not spend research effort re-reading what `get_brand` already returns.

Stop when new sources stop producing new language. Three sources that disagree beat ten that repeat each other.

## Building avatars

An avatar is one reader, not a segment. "Women 35-54 interested in wellness" is a media buying line, not an avatar. "Sarah, 42, quit three greens powders over the taste and now assumes they all taste like grass" is an avatar.

Keep them separate. A brand usually has three to five real readers, and blending them into one composite produces a page that speaks to nobody. Separate avatars are also what makes the conflict rule work: you can only select the right reader if the readers are distinct.

The save tool describes the fields; the judgment is in how you fill them. Give each avatar a short, stable id you would recognise next month (`taste-quitters`), because reusing an id refreshes that avatar and leaves the rest alone. Everything you learned that will not fit in the digest still belongs in the record: the full reasoning, the source detail, the material you had to cut. It never reaches a page, and it is what makes the next session start ahead of where you did rather than level with it.

Save the market-level findings alongside the avatars: recurring objections in customers' own words, competitors and what they claim or get criticized for, and verbatim customer phrases.

## Writing a digest

The digest is the only research that can reach a page, and it is capped. Write to the cap rather than against it, and write it to be read by a copywriter rather than stored by a database.

- Dense and specific. No preamble, no "this avatar represents".
- Who they are, what they have already tried, what stopped them buying, and the exact words they use.
- Concrete beats abstract. "Says 'it tastes like pond water'" beats "sensitive to taste".
- Leave out anything that is background rather than usable. The full picture belongs in notes.

A tight digest steers a writer harder than pages of raw notes. That is not a storage compromise, it is a quality one.

## Using research on a page

Research never auto-injects. To use an avatar, you pass its digest as `create_page`'s `context`, deliberately, once you have decided it matches.

Before you do, apply the conflict rule from SKILL.md:

- The user asked for a page aimed at one of your avatars, so pass that avatar's digest and no other.
- The user asked for a reader none of your avatars cover, so **pass no avatar**. Use the market-level material instead: objections, competitor claims, product facts. Those do not carry a conflicting persona.
- The user did not specify a reader, so either ask which one, or use the avatar the portfolio has not covered yet. Say which one you used.

Never pass two avatars. Never merge two digests into one. Never pass an avatar you had to argue yourself into.

## Ethics of the raw material

Everything you harvest shapes how the page talks. None of it becomes social proof. Do not turn a review you found into a testimonial on the page, do not attribute a quote to a person, and do not paraphrase someone's review into copy that reads as though a customer said it about this product.

Do not assume the product will stop you. Ratings and review counts are genuinely locked, but testimonial and review *text* is writable, because a user pasting in a real customer quote is a legitimate thing to do. Research is not that. The line between transcribing a quote the user handed you and laundering a quote you found is yours to hold, and it is the whole reason research is worth having.
