# Campus Customs: Usability Improvements

Four improvements to the shop: two on the website, two in the shopping
assistant. Each section says what we added and why it matters to a Campus
Customs shopper or to the business.

---

## 1. Filters and sorting on the Products page

**What we added:**

- **Filters:**
  - garment category: Hoodies, Crewnecks, T-Shirts, Quarter-Zips, Jackets & Fleece, Long Sleeves
  - color
  - size in stock
- **Sort** by price, low to high or high to low, or by name.
- **A live count**, such as "12 of 102 products".
- **One click to reset** everything.

The categories group the catalogue's 22 inconsistent garment labels (for
example, "hooded sweatshirt" and "pullover hoodie" both count as Hoodies), so
a filter finds everything that belongs in it. Colors are grouped into 9
families: "navy" and "navy blue" are both Navy, and "heather gray" and
"charcoal" are both Gray. The size filter only keeps items that actually have
that size in stock. Filters are saved in the page address, so they survive
opening a product and coming back, and can be shared as a link.

*Changed while building:*

- We added a sixth category, **Long Sleeves**, for 2 performance shirts that weren't really T-shirts.
- The color filter matches **any color visible on the item**, including the print. This is because the catalogue lists each product's visible colors, not colorways. For example, the charcoal Champion Full Zip Hood shows up under Navy because of its navy print.

**Why it helps:** with 102 products on one grid, a shopper looking for "a navy
crewneck in XL under $60" otherwise has to scroll and click into each item to
check sizes. Filters take them to buyable options in a few clicks. Filtering
by size in stock means they never fall for an item they can't buy, which
saves both a frustrating click and a lost sale.

**How to see it:**

1. Open **Products**.
2. Click **Hoodies**, then **Navy**, then **XL**, then choose **Sort by: Price, high to low**. The count reads "19 of 102 products", with the $88.00 hoodies first.
3. Add **Red & Coral** to see the "no products match" message and its **Clear filters** link.

---

## 2. Suggested questions in the chat

**What we added:** clickable starter questions in the chat panel that send
with one click.

- **Anywhere on the site:** general questions such as "What hoodies do you have?", "What's in stock in XL?" and "Anything under $40?"
- **On a product page:** questions about that item, such as "Is this in stock in my size?", "What sizes are left?" and "Do you have this in another color?"

**Why it helps:** most shoppers don't know what a store chatbot can do, so
they ignore it or ask something it can't answer. Starter questions show off
what it's good at, such as live stock, sizes and search, and get the first
question asked. Questions specific to a product reach shoppers at the moment
they're deciding to buy.

*Changed while building:* the questions sit in one row that scrolls
sideways, so on short screens they don't push the conversation out of view.
General questions disappear once the shopper has asked something.
Questions about a product always show on its page.

**How to see it:**

1. Open the chat on the **Home** page, then click **"What's in stock in XL?"**. It sends with one click, and the Products page shows all 77 items in stock in XL.
2. Open any product page, such as the Champion Reverse Weave Hoodie, and open the chat to see the four questions about that item.

---

## 3. In-stock alternatives when a size is sold out

**What we added:** a new agent tool, `find_alternatives`. When a shopper asks
for a size that's sold out, the assistant looks for similar products: the
same category, a similar price, and **that size in stock**. It shows them as
clickable product cards in the chat, without taking the shopper off the page
they're on.

**Why it helps:** "Sorry, XL is sold out" ends the conversation and loses the
sale. "XL is sold out in this one, but these three hoodies at the same price
have XL" keeps the shopper buying. About 24% of size slots in the catalogue
are at zero, so this comes up often.

**How to see it:**

1. Open the **Champion Reverse Weave Hoodie 1** product page, which is sold out in XS and XL.
2. In the chat, click **"Is this in stock in my size?"** and answer **XL**.
3. The bot says XL is sold out, then shows an **"In stock instead:"** list. It has 3 product cards (6 in total, at the same $68.00 price, all with XL in stock) and a "View all 6 on the page" link. You stay on the product page.

---

## 4. A fact check on every reply before it's sent

**What we added:** before a reply reaches the shopper, the backend checks
every price ("$68.00") and stock number ("only 2 left") in it against what the
database tools actually returned during that turn. If a number doesn't match,
or the bot stated a price without looking anything up, the reply is sent back
to the agent with the specific problem, and the agent redoes it. Replies that
pass show a small "checked against store data" badge.

**Why it helps:** a wrong price or a false "in stock" is the worst mistake a
shop assistant can make. It erodes trust, and it creates pricing disputes and
cancelled orders. The prompt already says "never invent a price". This check
enforces that rule in code rather than relying only on the model to follow
it.

*Changed while building:*

- **Allowed arithmetic.** Simple sums now pass: 2 to 10 of one item, two items added together, or a total of the quantities in one tool result ("96 XL hoodies across these 6"). Otherwise a correct total would be wrongly rejected.
- **Stricter stock check.** Stock numbers must match a real quantity field. A first version would accept any number the tools produced, so "only 3 left" slipped through because a product happened to have 3 sizes in stock.
- **Demo switch.** The live model followed the rules in every test, so a correction never happened naturally. We added an opt-in demo switch so graders can watch one.

**How to see it:**

- **Normal use.** Ask "How much is the Yale Mom Hoodie and how many are left in large?" The reply ("The Yale Mom Hoodie is $68.00, and there are 25 left in large") shows a green **"✓ Checked against store data · $68.00 · 25 left"** badge. The exact wording of the figures follows how the bot phrased them.
- **A correction.** Add the line `FACT_CHECK_DEMO=1` to the top-level `.env` and restart the backend. Then ask the price of any item, such as "How much is the Yale Bowl T-shirt?".
  - The first draft is deliberately given a wrong price ($37.00).
  - The fact check rejects it, and the agent redoes the answer.
  - The reply says $32.00, with an amber **"✓ Corrected once before sending, then checked"** badge.
  - The backend console shows `fact check failed (attempt 1): the price $37.00 was not returned by any tool this turn`.
  - Remove the line afterwards.
- **Without the app.** From `backend/`, run `python test_factcheck.py`. A scripted model gives a wrong price and quantity, and the check forces a correct second answer.
