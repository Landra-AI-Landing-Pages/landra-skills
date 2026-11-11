# Refining a page, and knowing when to hand off

Chat is a good control surface and a partial editor. The skill here is knowing which changes belong in the conversation and which belong in Landra's editor, and saying so instead of struggling.

## Three reads, three different jobs

Reaching for the wrong one is the most common way to waste a turn.

- **To let the user SEE the page**, use the visual read. It renders the real design, so it is the honest answer to "how does it look". Give them the link as well: on most surfaces the render sits inside a collapsed tool call, so a reply that depends on them seeing it can fail silently.
- **To answer questions about what the page SAYS**, use the text read. It includes copy that is not editable, which is exactly what you want when the question is about content rather than editing.
- **To prepare an edit**, use the editable-field read. It gives you the addressable fields an edit must target. It is not a display format, so do not paste it at the user.

## What editing from chat actually is

Text edits are direct replacements. Deterministic, free, instant. That has one consequence people misread:

**"Make this section more persuasive" is you rewriting the words, not Landra regenerating them.** No generation happens on Landra's side. So either propose specific replacement copy, get agreement, and apply it, or hand off to "Improve with Landra" in the editor, which reruns the real pipeline on that section. Do not present a text replacement as a regeneration.

The tools state which fields are open and which are refused; read them rather than guessing, and if an edit comes back rejected, that is a designed boundary and not something to work around. The one boundary you enforce yourself rather than the product enforcing it is customer voice: testimonial and review text is writable, and SKILL.md's truth protocol governs when you may write it.

## Structure

Sections can be added and removed from chat. Both are structural, so:

- A new section arrives with placeholder copy. Fill it in immediately and tell the user what you wrote. Leaving placeholder text on a page is worse than not adding the section.
- Removing a section deletes all its content. Confirm first unless the user named that exact section.
- **Removing the compliance disclosure is possible, and it is a decision, not an edit.** The tool will warn you. Stop and make sure the user means it, and offer to put it back. On a Landra-hosted page the disclosure is recomposed when the page is served, but a page pushed to Shopify or exported keeps the removal, so do not treat the warning as cosmetic.
- Undo exists but it is shallow. Do not rely on it to unwind a sequence of changes.

## When a write is refused

Two refusals are normal and neither means something is broken:

- **Something else is writing the page.** Another tab, the Landra editor mid-save, or a background job. The change is not applied rather than clobbering the other writer. This applies to text edits as much as structural ones. Tell the user and try again shortly; do not loop.
- **Images are still being generated.** The page is in flux, so writes wait. Let the images finish.

## Hand off to the editor for these

Say plainly that the editor is the right place, and give the link:

- **Anything visual.** Colors, fonts, layout width, section spacing, header treatment, announcement bar. You can show the user what the page looks like, but you cannot change how it looks.
- **Images.** Regenerating, editing or replacing an image happens in the Edit Image studio.
- **Genuine rewrites of a section.** "Improve with Landra" reruns the pipeline with the user's feedback, which is a different and better thing than you retyping the paragraph.
- **Reordering or hiding sections**, and any restructuring beyond adding and removing one. The Page Tree owns that.
- **Reusing a section across pages.** Saved sections live in the editor library.

Handing off is not a failure. A confident "that one's a two-click change in the editor, here's the link" is better service than a clumsy approximation in chat.

## Drafts, live pages, and publishing

Every edit saves to the draft. **A live published page does not change until it is published again.** This trips people up constantly: they edit a live page, look at the public URL, and see the old copy. Say it explicitly whenever you edit a published page.

Before publishing, check the page is actually finished, show the user what is about to go live, and get a real confirmation. Publishing also depends on the account's plan, so if the tool refuses, relay that plainly rather than retrying.

## Testing a variant

To A/B a page that works, duplicate it. The copy starts as an independent draft that does not inherit the original's live URL, so you can edit it and publish it separately without touching the page that is already running. Change one thing, not five, or the test tells you nothing.
