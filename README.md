# Landra Skills

Free Claude skills for DTC brands, from [Landra](https://landra.com) (the landing page builder Ezra Rufino runs).

## Product Image Audit

Paste a product page link. Claude pulls every image in your gallery in order, checks the live page, looks at each image, and tells you:
- what each image does for a buyer
- which shots your category needs that you're missing, ranked
- the order to put them in
- a shot brief for every missing image
- bugs like the wrong colour or shade showing in another variant's gallery

### Install in the Claude app
1. Download `product-image-audit.zip` from Releases. Leave it zipped.
2. In Claude: **Settings → Capabilities**. Turn on code execution, and allow network access so the skill can read your page.
3. **Customize → Skills → + → Upload a skill**, then pick the ZIP and switch it on.
4. Ask: "Audit the images on my product page: <link>"

If network access is off, the skill asks you for screenshots of your gallery instead.

### Install in Claude Code
Paste this into Claude Code:
```
https://github.com/Landra-AI-Landing-Pages/landra-skills.git
Clone this and add the product-image-audit skill.
```
Or: `git clone` the repo, then copy `skills/product-image-audit` into `~/.claude/skills/`.

Works best with Chrome installed: the skill takes screenshots of the live page to check what shoppers really see.

## What it won't do
It doesn't invent numbers, generate images, publish anything, or promise a conversion lift. It only reads public pages.

## License
MIT
