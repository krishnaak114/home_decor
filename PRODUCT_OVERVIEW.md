# Product Overview & Features

## What Exactly Is This Product?

**Name:** Home Decor AI Design Platform

**Simple Definition:** 
An e-commerce platform for home decor with AI-powered room visualization. Customers browse furniture, get AI-generated designs for their actual room, swap items with fast AI regeneration (8-12 seconds) to see alternatives, then buy what they love.

**The Core Idea:**
E-commerce platform of home decor with inclusive features of AI (room visualization, design suggestions, fast product swapping).

**What Makes It Special:**
- Upload your room photo + wall details → AI generates design in 8-12 seconds
- Don't like the sofa? Click a different one → AI regenerates in 8-12 seconds (fast swapping)
- AI auto-picks best products if you don't choose, or you can select specific items
- See EXACTLY how furniture looks in YOUR room before buying
- Living room decoration only (bedrooms, kitchen come in Phase 2)

---

## Phase 1 MVP (8-Week Solo Launch)

**Total Screens: 10-12** (focused, launch-ready)
**Development: Solo developer, full-time, 8 weeks**
**Philosophy: Launch small, iterate fast, add features based on real user feedback**

### **Screen 1: Home Screen** (Main screen - NO login required)
**Key Point:** Users can visit and browse WITHOUT signing in
- **Search bar** at top - Search products by name (simple text search)
- "Upload Your Room Photo" button (prominently placed, fits with layout)
  - When clicked → triggers login popup
- Product displays/catalogs:
  - All products grid (living room furniture)
  - Category-wise sections (Sofas, Tables, Lamps, Rugs, Curtains, etc.)
  - Sorted by: Newest First (default)
- Inspiration styles grid: Modern, Luxury, Minimalist, Scandinavian
- Simple hero section explaining what the platform does
- **Trust elements (if applicable):**
  - "X Designs Created" counter (starts at 0, grows naturally)
  - "Free Shipping" or "Easy Returns" badges (only if business offers these policies)

### **Screen 2: Login/Signup** (Triggered by actions)
**Shows when user:**
- Clicks "Upload Your Room Photo"
- Clicks "Save Design"
- Proceeds to checkout
**Options:**
- Google login (1 click)
- Phone OTP login
- Simple and fast (< 10 seconds)

### **Screen 3: Upload & Customize Room** (All-in-One Premium Experience)

**Part 1: Upload Room Photo**
- Camera capture or gallery upload
- Preview uploaded image

**Part 2: Room Details (Smart Input - Makes AI Faster)**
- **Wall length** (meters/feet dropdown) - AI understands space better
- **Wall colors** (text input: "Beige", "White", "Light Grey") - AI matches furniture colors
- **Room description** (optional text: "Modern, bright, large windows") - AI understands style preference

**Why ask users for this?**
- Provides crucial context for AI to make smarter suggestions
- Helps AI understand space dimensions and color compatibility
- With it: AI consistently delivers in 8-12 seconds with accurate results
- User gives context → AI makes better furniture recommendations

**Part 3: Select Products (Optional)**
- Live product carousel below (living room furniture only)
- Shows sofas, rugs, curtains, coffee tables, etc.
- User can:
  - **Select specific products** they like (tap to select)
  - **Or skip** (let AI auto-pick best items)

**Part 4: Generate Button**
- Shows "8 credits remaining" above button
- One large "Generate My Design" button
- Click → goes to loading screen
- **If 0 credits:** Shows modal:
  - "You've used all your free designs!"
  - "Buy more: ₹299 for 20 designs or ₹499 for 50 designs"
  - Payment button → Purchase flow
  - After successful purchase → Returns to generate button

**Example Flow:**
1. User uploads photo of empty living room
2. Enters: Wall length = 4.5m, Colors = "Beige and White", Description = "Modern, minimal"
3. Either selects a specific grey sofa OR leaves blank
4. Clicks "Generate My Design"
5. AI creates design in 8-12 seconds

### **Screen 4: AI Processing** (Premium Waiting Experience)
- Animated progress indicator
- Rotating text:
  - "Analyzing your room layout..."
  - "Matching furniture to your space..."
  - "Creating perfect design..."
- Makes 8-12 second wait feel premium (not annoying)

### **Screen 5: Design Result** (THE MAGIC SCREEN - Core Differentiator)

**Part 1: Your Generated Design**
- **Large preview image**: Room photo with AI-placed furniture
- **Design ID**: Saved automatically
- Small badges: Style name ("Modern"), Color palette

**Part 2: Fast Product Swapping** (Key Feature - Like Barbie But Faster)
- User sees design with AI-picked sofa
- User clicks "Change Sofa" button
- Modal opens showing 4-6 alternative sofas from catalog
- User taps different sofa → **AI regenerates design in 8-12 seconds**
- New design appears with different sofa, same room

**Example:**
1. AI picks "Modern Grey Sofa ₹25,000"
2. User doesn't like it → clicks "Change Sofa"
3. Sees options: Luxury Beige Sofa, Minimalist White Sofa, etc.
4. Taps "Luxury Beige Sofa"
5. Loading 8-12 seconds
6. New design with beige sofa appears
7. Can change again, or change rug/curtains too

**Why 8-12 seconds is acceptable:**
- User sees it's AI-generated (not pre-made template)
- Premium feel (AI working hard)
- Fast enough to try 3-4 options without frustration

**Part 3: Your Design Details**
- List of furniture in the design:
  - Sofa: "Modern Grey Sofa" - ₹25,000 [View] [Change]
  - Coffee Table: "Wooden Table" - ₹8,000 [View] [Change]
  - Rug: "Abstract Rug" - ₹5,000 [View] [Change]
  - Curtains: "Beige Curtains" - ₹3,500 [View] [Change]
  - Wall Art: "Modern Frame" - ₹2,500 [View]
  - Lamp: "Floor Lamp" - ₹4,000 [View]
- Total Design Value: ₹48,000

**Part 4: Action Buttons**
- "Save Design" (save for later)
- "Add All to Cart" (quick buy all items shown in design)

**Design Generation Credits:**
- **Every user gets:** 10 free design credits on signup
- **After 10 designs exhausted:** Buy more credits (₹299 for 20 designs, ₹499 for 50 designs)
- **Login required:** Must be logged in to generate designs (tracks credits)
- **Why?** Controls AI costs (Claude API ~₹2-3 per generation)
- **Display:** Shows "8 credits remaining" before each generation

**Example User Journey:**
1. AI generates living room with grey sofa, wooden table, beige rug
2. User likes table and rug, but wants different sofa
3. Clicks [Change] next to sofa
4. Sees 4-6 sofa options
5. Picks "Luxury Beige Sofa"
6. Waits 8-12 seconds (AI regenerates design)
7. New design appears with beige sofa (rest unchanged)
8. Perfect! Clicks "Add All to Cart"
9. Goes to checkout

### **Screen 6: Product List** (Browse All Furniture)
- **Search bar** at top - Search by product name (e.g., "grey sofa")
- **Sort dropdown** - Sort by: Price (Low to High), Price (High to Low), Newest First
- Grid of products (living room furniture only):
  - Each shows: Image, Name, Price, Rating (if reviews exist), "Add to Cart" button
- Clean, simple layout
- **Empty state:** "No products found. Try different keywords."

### **Screen 7: Product Detail Page**
- Large product image
- Product name, price, description
- Specifications (dimensions, material, colors available, stock status)

**Reviews Section (Basic but Essential):**
- Display average rating (e.g., 4.5/5 stars from 23 reviews)
- List recent reviews:
  - User name, star rating, comment, date
- **Leave a review** button (logged-in users only):
  - 5-star rating selector
  - Comment text box
  - Submit button

**Actions:**
- "Add to Cart" button (large, prominent)
- "See in My Room" button (triggers AI design with this product pre-selected)

**Example:**
Product: "Modern Grey Sofa"
Rating: 4.5/5 (23 reviews)
Recent review: "Amazing quality! Matches my design perfectly - Krishna A."

### **Screen 8: Saved Designs** (Logged-in users only)
- Grid view of all user's saved designs
- Each design card shows:
  - Design preview image
  - Style name ("Modern Living Room")
  - Date saved
  - Actions: [View] [Delete]
- Click "View" → Opens Screen 5 (Design Result) with that saved design
- **Empty state:** "No saved designs yet. Create your first design!"

### **Screen 9: User Profile** (Minimal - MVP Only)
- Display user name and email
- **"Design Credits: 8 remaining"** (prominent display)
- **"Buy More Credits"** button → Opens credit purchase modal:
  - Option 1: ₹299 for 20 designs
  - Option 2: ₹499 for 50 designs
  - Payment via Stripe/Razorpay
- "Logout" button
- "Send Feedback" link (opens simple form or mailto)
- Keep it super simple for MVP

### **Screen 10: Shopping Cart**
- List of items in cart:
  - Product thumbnail, name, price
  - Quantity selector (+ / -)
  - Remove button (X)
- **Cart Summary:**
  - Subtotal: ₹XX,XXX
  - Delivery: Free (or ₹XXX)
  - **Total: ₹XX,XXX**
- **Actions:**
  - "Continue Shopping" → back to products
  - "Proceed to Checkout" → go to checkout
- **Empty cart state:** "Your cart is empty. Start shopping!"

### **Screen 11: Checkout** (Simple 2-Step Flow)

**Step 1: Delivery Address**
- Form fields:
  - Full name
  - Phone number
  - Complete address (line 1, line 2, city, state, pincode)
  - Optional: "Save for future orders"
- "Continue to Payment" button

**Step 2: Payment**
- Shows cart summary (items + total)
- Payment method selection:
  - **Stripe** (Credit/Debit cards, international)
  - **Razorpay** (UPI, cards, wallets - India)
- "Place Order" button
- **Loading:** "Processing payment..." with spinner
- **Error handling:** "Payment failed. Please try again or try different method."

**Success → Screen 12**

### **Screen 12: Order Confirmation** (Success Page)
- Large success icon ✅
- "Order Placed Successfully! 🎉"
- **Order details:**
  - Order ID (e.g., #ORD123456)
  - Items ordered (thumbnails + names)
  - Total amount paid
  - Delivery address
  - Estimated delivery: 5-7 business days
- **Actions:**
  - "Continue Shopping" → back to home
- **Notification:** Email sent with order details
- **SMS notification:** "Your order #ORD123456 confirmed. Delivery in 5-7 days."

**Note for MVP:** No order tracking or history page - users get email with details. Order history added in Week 9 post-launch.

**Return & Refund Policy**
- Return window (e.g., 7 days)
- Return conditions
- Refund process
- Exchange policy

**Shipping & Delivery Info**
- Delivery timeline (e.g., 5-7 business days)
- Shipping charges
- Delivery areas covered
- Tracking information

**Contact & Support**
- Email: support@yourplatform.com
- Phone: +91-XXXXXXXXXX
- Business hours
- FAQ section (common questions)

---

---

## MVP Features (8-Week Solo Launch) - Focused & Launch-Ready

### **Core Features (Must-Have)**

✅ **Public Home Page**
- Browse all products without login
- Simple product grid (living room furniture)
- Search products by name
- Sort by price or newest
- Call-to-action: "Upload Your Room Photo"

✅ **User Authentication** (Triggered When Needed)
- Google login (one-click)
- Phone OTP signup (backup)
- Only required for: uploading photo, saving designs, purchasing

✅ **AI Room Design** (THE CORE DIFFERENTIATOR**
- Upload room photo (camera or gallery)
- Smart input form (wall length, colors, description) → Makes AI 40% faster
- User can select specific products OR let AI auto-pick best items
- AI generates design in 8-12 seconds
- Shows design overlaid on user's actual room photo
- Lists all furniture in design with prices

✅ **Fast Product Swapping** (Like Barbie, But AI-Powered)
- Don't like sofa in design? Click [Change]
- Shows 4-6 alternative sofas
- Pick one → AI regenerates in 8-12 seconds
- Can swap sofa, rug, curtains, tables, etc.
- Try multiple combinations until perfect

✅ **Design Credits System** (Controls AI costs while providing flexibility)
- Every new user: 10 free design credits
- After exhausted: Buy more (₹299 for 20, ₹499 for 50)
- Login required to generate (tracks credits)
- Shows remaining credits before each generation

✅ **Product Catalog** (Living Room Only)
- Browse all living room furniture
- Search by product name
- Sort: Price (low-high), Newest First
- Clean grid layout

✅ **Product Details + Reviews** (Basic But Essential)
- Product image, name, price, description
- Reviews section:
  - Star rating + comments from customers
  - Average rating display
  - Leave review (logged-in only)
- Add to Cart button

✅ **Save Designs**
- Save favorite designs to profile
- View/delete saved designs
- Each design saves the exact room + furniture combination

✅ **Shopping Cart**
- Add products to cart
- Change quantities
- Remove items
- See subtotal + delivery + total
- Proceed to checkout

✅ **Simple Checkout**
- Enter delivery address (name, phone, address, pincode)
- Choose payment (Stripe for cards, Razorpay for UPI/wallets)
- Place order
- Error handling (payment fails, etc.)

✅ **Order Confirmation**
- Success message with order ID
- Order summary (items, total, address)
- Email + SMS notification sent
- Option to continue shopping

✅ **User Profile** (Minimal)
- View design credits remaining
- Buy more credits (₹299 for 20, ₹499 for 50)
- View saved designs
- Logout
- Send feedback

✅ **Basic Legal** (Footer Links)
- Simple Privacy Policy (template-based for now)
- Basic Terms of Service
- Refund/Return info (text page)
- Contact info (email/phone)

✅ **Error Handling**
- Payment failure messages
- Upload error handling
- Empty cart state
- Empty saved designs state
- No search results found

---

### **Postponed to Post-Launch (Week 9+)**

📌 **Week 9-10 Additions:**
- Wishlist feature
- Order history page (track past orders)
- Advanced product filters (price range, color, material)
- Order tracking enhancements (detailed shipment tracking)

📌 **Week 11-12 Additions:**
- Design variations (show 3-4 style alternatives)
- Order tracking (shipped status, estimated delivery)
- Invoice download (PDF)
- Reorder functionality

📌 **Phase 2 (Month 3+):**
- Expand to other rooms (bedroom, kitchen, dining)
- Existing furniture masking (decor around real furniture - needs Computer Vision)
- Mobile app (React Native)
- Multiple design styles (modern, luxury, minimalist presets)

✅ **Admin Dashboard (Basic)**
- Add living room products only
- View orders
- Track sales

---

## Phase 2+ Features (After 8 Weeks) - NOT in MVP

❌ **Not in MVP but coming later:**
- Other room types (Bedroom, Kitchen, Dining Room, etc.)
- Advanced product filters (by style, material, color)
- Advanced search (by category, tags, attributes)
- Real-time order tracking with map
- Design sharing analytics
- Multiple design style variations
- Budget-aware recommendations
- Advanced analytics dashboard
- Mobile app (native iOS/Android)
- Push notifications
- Loyalty/rewards program
- Influencer/creator marketplace

---

## How Does It Actually Function? (MVP Version)

### **The Main Magic - Room Photo + AI Overlay**

**User Journey:**
1. Customer opens website (no login required)
2. Clicks "Get Started" or "Upload Your Room Photo"
3. **Login triggered** → Signs up with Google or phone OTP (quick, 10 seconds)
4. Upload screen appears → Takes/uploads room photo
5. Fills room details (wall length, colors, description)
6. Optionally selects specific products OR lets AI auto-pick
7. Clicks "Generate Design" → AI processes for 8-12 seconds with "Designing your space..." animation
8. AI shows customer their room WITH furniture overlaid on it
9. Design shows: Style name, Colors, Furniture pieces with prices
10. Customer can "Save Design", "Regenerate", "Change" individual items, or "Add to Cart"
11. Click "Add to Cart" or "View Furniture" to see product details and buy

---

## What You Provide for MVP

### **1. Furniture Products** (Minimum 40-50 items)
For each item:
- Name (e.g., "3-Seater Modern Grey Sofa")
- Price
- Category (Sofa, Table, Lamp, Art, Rug, Curtains)
- Photo (1 good product photo)
- Design style it matches (Modern, Luxury, Minimalist, etc.)

### **2. Design Styles** (At least 4-5)
Choose which styles to feature. Examples:
- Modern (clean, contemporary)
- Luxury (premium, elegant)
- Minimalist (simple, functional)
- Scandinavian (light, natural)
- Bohemian (colorful, eclectic, artistic)
- Industrial (raw, metal, vintage)
- Traditional (classic, elegant, detailed)

For each style:
- Style name
- 3-4 main colors
- Which products fit this style

### **3. Brand Info**
- Logo
- Brand colors (3-4 colors)
- Brand name

---

## Admin Dashboard (ESSENTIAL - Your Friend's Control Panel)

**Why Admin is Critical:**
- Your friend manages everything independently (no dependency on you)
- Add/edit products without touching code
- Process orders and update shipping status
- See what's selling, what's not
- **Full control from Day 1**

### **1. Products Management**

**Add New Product:**
- Product name (e.g., "Modern Grey 3-Seater Sofa")
- Price (₹)
- Category dropdown (Sofa, Table, Rug, Curtain, Lamp, Art, etc.)
- Style tags (Modern, Luxury, Minimalist, Scandinavian)
- Upload product image (drag & drop or browse)
- Description (material, dimensions, features)
- Stock quantity (how many available)
- Click "Save" → Product appears on website instantly

**Edit Existing Product:**
- Search for product by name
- Update price, stock, description
- Replace image if needed
- Mark as "Out of Stock" temporarily
- Changes reflected immediately on website

**Delete Product:**
- Remove product from catalog
- Confirmation prompt (prevent accidental deletion)

**Example Workflow:**
- Friend gets new sofa from supplier → Login to admin → Add Product → Upload image, set price ₹32,000 → Save → Live on website in 2 minutes

### **2. Order Management (Simple Manual Tracking)**

**View All Orders:**
- Table showing:
  - Order ID (#ORD123456)
  - Customer name + phone
  - Items ordered (thumbnails)
  - Total amount
  - Order date
  - **Current status** (Ordered / Shipped / Delivered)
  - Actions: [View Details] [Update Status]

**Update Order Status (Manual Tracking):**
- Click "Update Status" next to order
- Dropdown appears: 
  - ⏳ **Ordered** (initial status when payment successful)
  - 📦 **Shipped** (when package handed to delivery partner)
  - ✅ **Delivered** (when customer confirms receipt)
- Select new status → Click "Update"
- **Customer gets SMS/Email notification** automatically with status change
- Example: "Your order #ORD123456 has been shipped! Expected delivery in 3-5 days."

**Order Details View:**
- Customer info (name, phone, address)
- Items ordered (with images, quantities, prices)
- Payment method (UPI / Card)
- Payment ID (for reference)
- Total amount paid
- Order date and time
- Current status
- Full delivery address

**Example Workflow:**
1. Customer places order → Status automatically set to "Ordered"
2. Your friend packs items, gives to delivery partner → Login admin → Find order → Change status to "Shipped" → Customer gets SMS
3. Customer receives → Friend changes status to "Delivered"
4. Done!

### **3. Sales & Analytics Dashboard**

**Quick Stats (Top of dashboard):**
- **Today's Sales:** ₹12,500 (3 orders)
- **This Month:** ₹1,85,000 (42 orders)
- **Total Designs Created:** 287
- **Total Customers:** 156

**Best Selling Products:**
- Shows top 5 products by sales
- Product name, total units sold, revenue
- Helps friend know what to restock

**Recent Orders (Last 10):**
- Quick glance at latest orders
- Click to view details or update status

**Revenue Chart:**
- Simple bar chart showing sales per day/week/month
- Helps track growth

### **4. Customer List** (Simple Admin Feature)

- View all registered customers
- See: Name, email, phone, signup date
- Total orders placed by each customer
- Simple table view (no complex features)

### **5. Design Analytics** (What's Working)

- Total designs generated (all time)
- Designs created today/this week
- Most popular design styles (Modern: 65%, Luxury: 25%, Minimalist: 10%)
- Average design value (e.g., ₹48,000)
- Design-to-purchase conversion rate (30% of designs lead to purchase)

---

## Admin Login & Security

**Separate Admin Portal:**
- URL: yourdomain.com/admin (separate from main site)
- Secure login (email + password + 2FA optional)
- Only your friend has access
- Can add multiple admin users later (if team grows)

**What Admin CANNOT Do (Security):**
- Cannot access customer payment details (handled by Stripe/Razorpay)
- Cannot see customer passwords (encrypted)
- Cannot modify order amounts after payment

**What Admin CAN Do:**
- Everything related to products, orders, content
- Full independence to run the business

---

## Summary Tables

### **Customer-Facing Screens (10-12 for MVP)**

| Screen | Purpose | Key Feature |
|--------|---------|------------|
| **1. Home** | Entry point | Product gallery + search + upload CTA |
| **2. Login** | Authentication | Google + Phone OTP (triggered only when needed) |
| **3. Upload & Design** | AI magic | Photo + room details + optional product selection |
| **4. Loading** | Premium feel | Animated progress while AI works (8-12 seconds) |
| **5. Design Result** | **Core value** | Room with furniture + fast swapping (8-12 sec regeneration) |
| **6. Product List** | Browse | Search + sort by price/newest + clean grid |
| **7. Product Detail** | Product info | Image + price + reviews + Add to Cart |
| **8. Saved Designs** | Retention | View/delete user's saved designs |
| **9. Profile** | Account | View credits + buy more + logout + feedback |
| **10. Cart** | Shopping | View/edit items + quantities + totals |
| **11. Checkout** | Purchase | Address form + payment (Stripe/Razorpay) |
| **12. Order Confirmation** | Success | Success message + email/SMS notification |

**Plus Essential Admin Panel (Separate Portal):**
- Product management (add/edit/delete)
- Order management (view, update status: Ordered → Shipped → Delivered)
- Sales analytics dashboard
- Customer list

**Plus Basic Legal (Footer Links, Not Screens):**
- Privacy Policy, Terms of Service, Contact Info (simple text pages)

---

**What Makes This MVP Complete:**
- ✅ E-commerce platform with AI (not AI platform with shopping)
- ✅ See furniture in YOUR room before buying (core differentiator)
- ✅ Fast product swapping (8-12 seconds - feels premium, not frustrating)
- ✅ AI auto-suggests OR user picks products (flexibility)
- ✅ Living room only (focused launch, expand later)
- ✅ Complete shopping flow (browse → design → cart → buy → confirmation)
- ✅ Basic reviews (builds trust)
- ✅ Admin independence (friend manages everything)
- ✅ Achievable in 8 weeks solo (realistic, not overambitious)

---
---

## How Does It Actually Work? (Real Examples)

### **Example 1: User Gets AI Design, Swaps Items, Buys**

**Starting point:** Priya wants to decorate her living room

1. **Visits website** → Sees home page with product gallery, clicks "Upload Your Room"
2. **Login prompt** → Signs in with Google (2 seconds)
3. **Upload screen** → Takes photo of empty living room with phone
4. **Fills details:**
   - Wall length: 4.5 meters
   - Wall colors: "Beige and white"
   - Description: "Modern, bright, lots of natural light"
   - Skips product selection (lets AI decide)
5. **Clicks "Generate Design"** → Waits 8-12 seconds (sees "Designing your space..." animation)
6. **AI Result:**
   - Shows room photo with furniture overlaid
   - Style: "Modern Minimalist"
   - Furniture: Grey sofa (₹28K), wooden table (₹8K), abstract rug (₹5K), floor lamp (₹4K), beige curtains (₹3.5K), wall art (₹2.5K)
   - Total design value: ₹51,000
7. **Likes everything except sofa** → Clicks [Change] next to sofa
8. **Sees 5 alternatives** → Picks "Luxury Beige Sofa ₹35K"
9. **Waits 8-12 seconds** → New design appears with beige sofa (rest unchanged)
10. **Perfect!** → Clicks "Add All to Cart"
11. **Adjusts cart** → Removes wall art (too expensive), keeps rest
12. **Checkout** → Enters address, pays ₹46,500 with UPI
13. **Success!** → Gets email + SMS confirmation, delivery in 5-7 days

**Total time:** ~8 minutes from landing to purchase

---

### **Example 2: User Browses Products, Then Uses AI**

**Starting point:** Ravi browsing website for sofas

1. **Home page** → Searches "grey sofa" in search bar
2. **Product list** → Sees 8 grey sofas, sorts by "Price: Low to High"
3. **Clicks on "Modern Grey Sofa ₹25K"** → Sees product details, 4.5★ rating (18 reviews)
4. **Reads review:** "Amazing quality! Delivered fast" - Krishna A.
5. **Not sure if it fits his room** → Clicks "See in My Room" button
6. **Login prompt** → Signs in with Google
7. **Upload room photo** → Takes photo of living room
8. **Fills details** → Wall 5m, Colors "White", Description "Modern"
9. **Product pre-selected** (the grey sofa he was viewing) → AI uses that specific sofa
10. **Clicks "Generate"** → Waits 8-12 seconds
11. **Sees design** → Grey sofa looks perfect in his room! AI also suggested matching rug and curtains
12. **Likes it!** → Adds just the sofa to cart (₹25,000)
13. **Checkout** → Pays with card
14. **Done!**

**Total time:** ~6 minutes

---

### **Example 3: Admin (Your Friend) Manages Order**

**Starting point:** Your friend receives notification of new order

1. **Email notification:** "New order #ORD789456 - ₹46,500"
2. **Logs into admin panel** → yourdomain.com/admin
3. **Dashboard shows:**
   - Today's sales: ₹46,500 (1 order)
   - New order appears in "Recent Orders" list
4. **Clicks on order #ORD789456** → Views details:
   - Customer: Priya Sharma, Phone: +91-98XXXXXXX
   - Items: Grey Sofa (₹28K), Wooden Table (₹8K), Rug (₹5K), Lamp (₹4K), Curtains (₹3.5K)
   - Total: ₹46,500
   - Address: 123 MG Road, Bangalore - 560001
   - Payment: UPI (confirmed)
   - **Status: Ordered** ⏳
5. **Friend packs items, arranges delivery partner**
6. **Updates status** → Clicks "Update Status" dropdown → Selects "Shipped" 📦 → Saves
7. **System automatically:**
   - Sends SMS to Priya: "Your order #ORD789456 has been shipped! Delivery in 3-5 days."
   - Sends email with tracking info
8. **3 days later:** Customer receives items
9. **Friend updates status** → Changes to "Delivered" ✅
10. **Done!** Customer happy, order completed

**Time spent:** 2 minutes to process order, 1 minute to update status

**Friend's independence:** No need to call you or touch code. Everything self-service! ✅

---

### **Example 4: Admin Adds New Product**

**Starting point:** Your friend gets new sofa collection from supplier

1. **Logs into admin panel** → yourdomain.com/admin
2. **Clicks "Products" → "Add New Product"**
3. **Fills form:**
   - Product name: "Scandinavian Oak Sofa"
   - Price: ₹32,000
   - Category: Sofa
   - Style tags: Scandinavian, Modern
   - Stock quantity: 15
   - Description: "3-seater solid oak sofa with beige cushions, 210cm × 90cm × 85cm"
   - Upload image (drag & drop product photo)
4. **Clicks "Save"** → Product published instantly
5. **Result:**
   - Product appears on website product grid immediately
   - AI can now use this sofa in designs
   - Customers can search, view, buy

**Time:** 2-3 minutes per product

**Friend's power:** Complete control over product catalog! ✅

---

## Summary - 8-Week Solo MVP

**Customer-Facing Screens (10-12):**

| Screen | Purpose | Key Feature |
|--------|---------|------------|
| **1. Home** | Entry point | Product gallery + search + upload CTA |
| **2. Login** | Authentication | Google + Phone OTP (triggered only when needed) |
| **3. Upload & Design** | AI magic | Photo + details + optional product selection |
| **4. Loading** | Premium feel | Animated progress while AI works |
| **5. Design Result** | **Core value** | Room with furniture + fast swapping (8-12 sec) |
| **6. Product List** | Browse | Search + sort + clean grid |
| **7. Product Detail** | Product info | Image + price + reviews + Add to Cart |
| **8. Saved Designs** | Retention | View/delete saved designs |
| **9. Profile** | Account | Credits balance + buy more + logout |
| **10. Cart** | Shopping | View/edit items + totals |
| **11. Checkout** | Purchase | Address + payment (Stripe/Razorpay) |
| **12. Order Success** | Confirmation | Success message + email/SMS notification |

**Admin Panel (Essential - Your Friend's Control Center):**

| Feature | What It Does | Why Essential |
|---------|--------------|---------------|
| **Product Management** | Add/edit/delete products with images | Friend runs catalog independently |
| **Order Dashboard** | View all orders with customer details | See what needs to be shipped |
| **Order Tracking** | Update status: Ordered → Shipped → Delivered | Customers get auto-notifications |
| **Sales Analytics** | Daily/monthly sales, popular products | Know what's selling |
| **Customer List** | View registered customers | Understanding user base |

**Plus Basic Legal (Footer Links, Not Separate Screens):**
- Privacy Policy, Terms of Service, Contact Info (simple text pages)

---

## What You Need to Provide (Before Week 1)

### **1. Product Catalog (Minimum 40-50 items)**

**Living Room Furniture:**
- 10-15 Sofas (various styles: modern, luxury, minimalist)
- 5-8 Coffee Tables
- 5-8 Rugs
- 5-8 Curtains
- 3-5 Floor Lamps
- 3-5 Table Lamps
- 5-8 Wall Art pieces
- 3-5 Cushions/Throws
- 2-3 Bookshelves (optional)

**For each product provide:**
- Name (e.g., "Modern Grey 3-Seater Sofa")
- Price (in ₹)
- One good quality image (square, 1000x1000px minimum)
- Brief description (50-100 words: material, dimensions, features)
- Category
- Style tag (Modern/Luxury/Minimalist/Scandinavian)

### **2. Design Styles (Pick 3-4 to start)**
- Modern (recommended)
- Minimalist (recommended)
- Luxury (optional)
- Scandinavian (optional)

### **3. Brand Assets**
- Logo (PNG with transparent background)
- Brand name
- 3-4 brand colors (hex codes)

### **4. Business Information**
- Company/Business name
- GST number (for invoices)
- Support email
- Support phone number
- Business address

### **5. Payment Accounts** (Can set up in Week 6-7)
- Stripe account (for card payments)
- Razorpay account (for UPI/wallets)

### **6. Legal Content** (Templates OK, customize later)
- Privacy Policy (use template, add company name)
- Terms of Service (use template, add company name)
- Return/Refund policy text
- Shipping policy text

---

## Next Steps - Let's Launch! 🚀

**Ready to start 8-week build?**

**Week 1-2:** Database + Auth + Home + Products
**Week 3-4:** AI Design Generation + Fast Swapping
**Week 5-6:** Cart + Checkout + Payments
**Week 7:** Reviews + Admin Panel + Polish
**Week 8:** Testing + Bug Fixes + Deploy + LAUNCH

**After you provide:**
✅ 40-50 product items with images
✅ Brand logo + colors
✅ Business info
✅ (Optional) Legal policy templates

**We can start Week 1!**

All documents aligned and ready for your friend to review or send to dev team (if you hire help).
