# KDP Automation - Complete Workflow Update

## ✅ What's Fixed

The automation now performs the **complete end-to-end workflow**:

### 1. Book Details ✓
- Fills title, subtitle, author info
- Sets categories
- Adds keywords and description
- Marks as low-content

### 2. Content Upload ✓
- Uploads interior PDF
- Uploads cover PDF (color-specific)

### 3. AI Generation ✓ (NEW)
- **Selects "Yes, I want to generate it by AI"** instead of "No AI"
- Clicks "Save and Continue"
- Waits for preview to load (up to 120 seconds)
- Clicks preview button
- Accepts/closes preview

### 4. Pricing & Publishing ✓ (NEW)
- Navigates to pricing page
- Selects "All territories"
- **Sets price to $7.99 USD** (from add_notebook.py)
- **Clicks "Publish Your Paperback Book"**

### 5. Batch Processing ✓ (NEW)
- **Removed the `break` statement**
- Now processes **ALL 28 colors** automatically
- 5-second pause between each book

## 📝 Key Changes Made

### kdp_automation.py

1. **Line 305-348**: AI Generation Selection
   - Changed from selecting "No AI" to "Yes, generate by AI"
   - Added preview handling workflow
   - Robust error handling with fallbacks

2. **Line 352-398**: New `fill_pricing_page()` function
   - Automates territory selection
   - Sets USD price from configuration
   - Clicks publish button

3. **Line 432-434**: Pricing Integration
   - Calls `fill_pricing_page()` with price from add_notebook.py
   - Added success confirmation message

4. **Line 439**: Removed Break Statement
   - Now processes all colors in the COLORS list
   - No manual intervention needed between books

5. **Line 4**: Added ActionChains Import
   - Properly imports ActionChains for keyboard interactions

## 🚀 How to Run

```bash
uv run kdp_automation.py
```

The script will:
1. Open Chrome with your saved profile
2. Log in to KDP (if needed)
3. For EACH of the 28 colors:
   - Create new book
   - Fill all details
   - Upload interior and cover
   - Select AI generation
   - Handle preview
   - Set price to $7.99
   - Publish the book
4. Wait for user input before closing browser

## ⚙️ Configuration

All settings are in `add_notebook.py`:

- **PRICE_IN_USD**: $7.99 (line 67)
- **BOOK_TITLE**: "Notebook: Things I'd like to tell my cat when I'm at work"
- **AUTHOR**: Michal Lipinski
- **KEYWORDS**: Funny cat lover gifts, etc.
- **CATEGORIES**: Activity Books, Journal Writing, Humor

## 🎨 Colors Processed

28 colors total:
- Best Sellers: Sage Green, Terracotta, Lavender Mist, Dusty Pink, Navy Blue
- Pastels: Periwinkle, Mint Green, Ballet Slipper, Lemon Chiffon, Mauve, Sky Blue
- Earth: Sand Beige, Olive Green, Brown Sugar, Tan, Ochre, Slate Gray
- Pop: Hot Pink, Electric Cyan, Sunset Orange, Chartreuse, Electric Purple
- Dark: Charcoal, Forest Green, Burgundy, Dark Plum, Cobalt Blue, Indigo

## ⚠️ Important Notes

1. **Manual Monitoring**: Watch the first book to ensure selectors are correct
2. **Preview Timing**: The preview wait is set to 120 seconds - adjust if needed
3. **Error Recovery**: If one color fails, the script continues to the next
4. **Browser Profile**: Uses `./chrome_profile` to maintain login state
5. **Credentials**: Currently hardcoded in line 353-354 (consider using environment variables)

## 🔧 Troubleshooting

If the automation fails at a specific step:

1. **AI Selection Fails**: The CSS selector on line 309 may need adjustment
2. **Preview Button Not Found**: Adjust XPath on line 327-328
3. **Price Input Missing**: Check XPath on line 378
4. **Publish Button Error**: Verify XPath on line 389

To debug: Watch the browser and check console output for specific error messages.

## ✨ Result

You should now have 28 published books, one for each color, all priced at $7.99 USD!
