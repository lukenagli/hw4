# Campus Customs: Design

**Concept: "The Varsity Print Shop."** Visiting the site should feel like
walking into the shop on Broadway. Jackets hang on a rack with manila hang
tags, college patches are stitched onto felt, a pennant hangs over the door,
and Stitch helps you at the counter under a striped awning. Every decorative
element is original CSS or SVG. We used no Campus Customs logo, images or
layout, and no official Yale marks or mascot art. The only Yale marks on the
site are on the shop's own product photos.

Each change is listed with why it should help a customer stay and buy.

## Type and color

- **Collegiate display font plus a readable body font.** Headings, prices and sizes use **Graduate**, a varsity block letter. Body text uses **Inter**. Sizes step up by about 1.25x (body 1rem, section 1.9rem, page title 3rem, hero 4.6rem).
  *Why:* the varsity letters set the shop's mood at a glance, and Inter keeps product details easy to read. The clear size steps tell the eye where to look first: headline, then price, then details.
- **Yale blue + warm cream base, with one accent: varsity gold, used only on things you can click.** That means buttons, "Ask Stitch", the Send button, suggestion chips, link underlines and keyboard focus rings. Every text and background pair passes WCAG AA, from 5.3:1 (sold-out size text) to 15.3:1 (body text).
  *Why:* when gold always means "clickable", shoppers learn the pattern on the first screen, and the buy-path actions stand out from the decoration.

## Hierarchy

- **Home hero with one obvious action.** A big felt panel, the headline "Varsity gear, pressed with pride.", one gold **Shop the collection** button, and a quiet text link to ask Stitch. On the right, a featured hoodie hangs on a hanger with a hang-tag price.
  *Why:* one clear next step means visitors don't have to choose between competing buttons, and the hanging product shows real stock and a real price straight away.
- **"How the shop works" strip** (pick your corner of Yale → check live sizes → ask at the counter).
  *Why:* it sets expectations in three seconds and points out the two things that make this shop different: live stock and the assistant.
- **Product page: a "buy box" for price, stock and sizes.** It comes right after the name, in a raised card: a large hang-tag price, a one-line stock summary ("In stock in 5 of 6 sizes · Hurry: XL (2) almost gone"), then the size chips. The description and colors come after. On phones the photo is shorter, so the price shows on the first screen (it sits at 648px on a 375×812 phone).
  *Why:* "how much?" and "is my size there?" are what decide a purchase. Putting them first, with a gentle low-stock nudge, removes friction and adds healthy urgency.

## Product presentation

- **Prices as manila hang tags.** Each price sits on a notched, punched tag clipped to the card corner, set in Graduate. It swings slightly on hover.
  *Why:* it ties the price to the shop concept and makes the price the second thing you notice on every card.
- **Size chips that show three states clearly:**
  - available: solid blue outline, green "In stock"
  - low stock (5 or fewer): dashed amber outline, "Only 2 left"
  - sold out: striped grey, size crossed out, red "Sold out"

  A small legend sits underneath. The states differ in border, pattern and wording, not only color.
  *Why:* shoppers can see their size in a single glance, sold-out sizes don't cause disappointment at checkout, and low-stock chips encourage buying now. It also works for color-blind shoppers.
- **Larger, zoomable product image.** The photo takes the wider column in a stitched frame. Hover zooms 2.2x toward the pointer, and tap or Enter toggles the zoom. A pill hint says "Hover or tap to zoom".
  *Why:* apparel shoppers want to check the print, stitching and fabric before buying. Zoom answers "what does it really look like?" without leaving the page.
- **Cards** have a stitched photo frame, a category label ("HOODIE"), the name, a two-line description, and a rubber-stamp "SOLD OUT" mark when nothing is left.
  *Why:* consistent cards make the grid quick to scan, and the stamp flags dead ends before a click.
- **Category "patches" on Home** are blue felt patches with stitched edges and a round product photo, for all six categories.
  *Why:* a fast, visual way into the catalogue that matches the concept.
- **Filters as a "Sort the rack" slip.** The Problem 9 filters sit on a labeled order slip, with color swatches and size chips in the display font. On phones each filter row scrolls sideways.
  *Why:* filtering looks like part of the shop rather than a generic form, and it stays usable with one thumb.

## Motion (quick, and off for reduced-motion users)

- **Cards lift on hover.** They rise 6px with a deeper shadow, the photo zooms slightly and the hang tag swings. Category patches tilt.
  *Why:* the feedback says "this is clickable" and makes browsing feel tactile.
- **Chat results deal onto the page one after another.** When Stitch finds products, the page header changes to "Pulled from the shelves by Stitch / Results for …". The cards then fly in 55ms apart (the delay stops growing after 16 cards, so 23 results finish in under 1.3 seconds). The matching mini cards in the chat bubble also deal in, one by one.
  *Why:* the visible cause and effect between "I asked" and "the shelf filled up" makes the link between chat and page obvious, and makes the assistant feel useful.
- **Smooth page transitions.** Each page fades and rises in over 0.24 seconds. The chat panel slides up when opened, bubbles fade in, and the "Ask Stitch" button pops in once on load.
  *Why:* it feels polished without slowing anyone down. Every animation is under half a second.
- **Reduced motion respected.** With `prefers-reduced-motion: reduce`, all animations and transitions are cut to an instant, hover movement is turned off, and the results scroll jumps instead of gliding.
  *Why:* it's comfortable for people who get motion sickness, and it's the accessible default.

## Chat: the shop counter

- **The assistant has a name and an original icon.** It's **Stitch**, shown as a round patch with a needle threading a looped "S". The panel header reads "Stitch / At the Campus Customs counter", under a blue-and-cream scalloped awning. The launcher is a gold "Ask Stitch" pill.
  *Why:* a named, friendly helper is more inviting to talk to than a generic "chat" bubble, which means more questions asked and more products found. The system prompt also tells the bot it's Stitch.
- **Clean bubbles with an avatar.** Stitch's replies are white with the small patch icon beside them. The customer's messages are Yale blue. The typing indicator reads "Stitch is checking the shelves" with bouncing dots.
  *Why:* it's clear who said what, and the typing line makes the wait feel like someone is working on it.
- **Compact product cards in the chat.** Each has a thumbnail, the name and a mini hang-tag price, and links to the product page, with "View all N on the page" below.
  *Why:* shoppers can jump straight to an item from the conversation.
- **"Ask Stitch" entry points** on the hero, the counter band, the footer, and **"Ask Stitch about this item"** in the product buy box. The last one opens the chat and asks about that product straight away.
  *Why:* help is offered at the moment of doubt, which is right next to the size chips.

## Header, footer and other pages

- **The header is a shop sign.** It has the stitched "CC" patch logo, the shop name in Graduate, "Varsity print shop · New Haven", and a letterman cuff stripe under it. The active page is marked with a stitched underline. On phones and tablets the nav becomes a strip that scrolls sideways.
  *Why:* a strong, consistent brand frame on every page that never covers content on small screens.
- **Felt footer** with the patch logo, an "Ask Stitch at the counter" link and a cuff stripe. Login links are hidden once you're signed in.
  *Why:* the footer is the last chance to point a hesitant visitor to help.
- **About** uses a felt header with a pennant and blue felt "value patches". **Log in / Create account** are styled as membership cards with a cuff stripe and stitched border.
  *Why:* the concept carries through every page, so the site feels like one shop rather than a template.

## Checked after the redesign (2026-10-06)

- **Pages:** Home, Products, a product page and About render at phone (375px), tablet (768px) and desktop widths. The header was fixed so the nav no longer runs off the edge at tablet width.
- **Filters:** Hoodies + XL gives 21 of 102, and the filters still live in the URL.
- **Product page:** size chips match the database (Sailor Bulldog hoodie: L sold out, XL "Only 2 left"). Zoom scales 2.2x.
- **Chat search:** "Show me navy crewnecks under $60" gives 23 cards dealt onto Products, 3 cards in the chat, and a green fact-check badge. Clicking a chat card or a page card opens the right product page, and Back keeps both the results and the chat.
- **Accounts and history:** logging in as Dan restored all 10 saved messages, with their product cards.
- **"Ask Stitch about this item":** it opened the chat and asked about the Yale Dad Hoodie. The reply's sizes matched the database.
- **Errors:** no console errors. All contrast pairs pass WCAG AA.
