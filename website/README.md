# SNAPPY Marketing Website

Professional marketing website for SNAPPY - Billing Software for Legal Professionals.

## 🚀 Quick Start

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Installation

```bash
# Navigate to website directory
cd website

# Install dependencies
npm install

# Start development server
npm run dev
```

The website will be available at `http://localhost:3000`

## 📁 Project Structure

```
website/
├── src/
│   ├── components/
│   │   ├── Navbar.tsx       # Navigation bar
│   │   └── Footer.tsx       # Footer component
│   ├── pages/
│   │   ├── Home.tsx         # Landing page
│   │   ├── Download.tsx     # Download page with installation guide
│   │   ├── Pricing.tsx      # Pricing plans (₹400/1000/1500)
│   │   ├── Support.tsx      # Contact form (Google Sheets integration)
│   │   ├── About.tsx        # About Parth Nuwal & SNAPPY
│   │   ├── Demo.tsx         # Product demo & screenshots
│   │   └── Admin.tsx        # Admin dashboard (password protected)
│   ├── App.tsx              # Main app with routing
│   ├── main.tsx             # React entry point
│   └── index.css            # Global styles
├── index.html               # HTML template
├── package.json             # Dependencies
├── vite.config.ts          # Vite configuration
├── tailwind.config.js      # Tailwind CSS config
└── tsconfig.json           # TypeScript config
```

## 📄 Pages Overview

### 1. Home (`/`)
- Hero section with CTA buttons
- Feature showcase (6 key features)
- Benefits section with stats
- Testimonials from users
- Final CTA section

### 2. Download (`/download`)
- Windows installer download button
- System requirements
- Installation guide (5 steps)
- Important notes (offline capability, updates, Windows Defender)
- Screenshot placeholder

### 3. Pricing (`/pricing`)
- 4 pricing tiers: Trial (Free), Starter (₹400), Pro (₹1000), Enterprise (₹1500)
- Feature comparison
- FAQs section
- Annual billing discount (20% off)

### 4. Support (`/support`)
- Contact form (Name, Email, Subject, Message)
- Google Sheets integration (TODO: See below)
- Contact information (email, phone, location)
- Business hours
- Priority support info

### 5. About (`/about`)
- Founder bio: Parth Nuwal
- Company mission & values
- Journey timeline
- Stats & achievements
- Social links (Email, LinkedIn, GitHub)

### 6. Demo (`/demo`)
- Product demo video placeholder
- Key features overview
- Step-by-step walkthrough (4 steps)
- Screenshots gallery (6 placeholders)
- User testimonial

### 7. Admin (`/admin`)
- Password-protected dashboard (password: `snappy2025`)
- Website analytics:
  - Total visitors, form submissions, downloads, active users
  - Top pages with traffic percentage
  - Recent form submissions table
  - Traffic chart placeholder
- Note: Uses localStorage for simple auth (production needs proper authentication)

## 🎨 Design System

### Colors
- Primary Blue: `#2563eb` (blue-600)
- Secondary Indigo: `#4f46e5` (indigo-600)
- Gradients: blue-600 → indigo-600

### Typography
- Font: Inter (from Google Fonts)
- Headings: Bold, various sizes
- Body: Regular, text-gray-600/700

### Components
- Responsive navbar with mobile menu
- Footer with 4 columns (About, Quick Links, Support, Contact)
- Gradient logo with "S" icon
- Consistent button styles (primary blue, outline)

## 🔧 Configuration

### Tailwind CSS
Custom primary color palette configured in `tailwind.config.js`:
```js
colors: {
  primary: {
    50: '#eff6ff',
    // ... through 900
  }
}
```

### Vite
Port configured to `3000` in `vite.config.ts`

### TypeScript
Strict mode enabled with ES2020 target

## 🚀 Deployment

### Deploy to Vercel

1. **Push to GitHub**:
```bash
git add .
git commit -m "Add SNAPPY marketing website"
git push origin main
```

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Configure:
     - Framework Preset: Vite
     - Root Directory: `website`
     - Build Command: `npm run build`
     - Output Directory: `dist`
   - Deploy!

3. **Custom Domain** (optional):
   - Add your domain in Vercel dashboard
   - Update DNS settings

### Deploy with Azure Static Web Apps

```bash
# Install Azure CLI
npm install -g @azure/static-web-apps-cli

# Deploy
swa deploy --app-location website --output-location dist
```

## ✅ TODO Before Production

### Critical
- [ ] Replace all placeholder images with actual screenshots
- [ ] Add real product demo video
- [ ] Integrate Google Sheets for Support form (see instructions below)
- [ ] Add actual download link for SNAPPY-Setup.msi
- [ ] Update contact information (phone number, email)
- [ ] Add real social media links
- [ ] Implement proper admin authentication (replace localStorage)

### Google Sheets Integration

To integrate the Support form with Google Sheets:

1. **Create Google Sheet**:
   - Create a new Google Sheet
   - Add columns: Timestamp, Name, Email, Subject, Message

2. **Create Apps Script**:
   - Tools → Script editor
   - Paste this code:
   ```javascript
   function doPost(e) {
     var sheet = SpreadsheetApp.getActiveSheet();
     var data = JSON.parse(e.postData.contents);
     sheet.appendRow([
       new Date(),
       data.name,
       data.email,
       data.subject,
       data.message
     ]);
     return ContentService.createTextOutput(
       JSON.stringify({ success: true })
     ).setMimeType(ContentService.MimeType.JSON);
   }
   ```

3. **Deploy Web App**:
   - Deploy → New deployment
   - Type: Web app
   - Execute as: Me
   - Who has access: Anyone
   - Copy the Web App URL

4. **Update Support.tsx**:
   Replace the TODO section in `handleSubmit`:
   ```typescript
   const response = await fetch('YOUR_GOOGLE_SCRIPT_URL', {
     method: 'POST',
     headers: { 'Content-Type': 'application/json' },
     body: JSON.stringify(formData),
   });
   ```

### Optional Enhancements
- [ ] Add Google Analytics for traffic tracking
- [ ] Implement real-time chat support (e.g., Tawk.to)
- [ ] Add blog section for SEO
- [ ] Create documentation pages
- [ ] Add FAQs page
- [ ] Implement email newsletter signup
- [ ] Add more testimonials with photos
- [ ] Create video tutorials
- [ ] Add multi-language support (Hindi + English)

## 🔒 Admin Dashboard

**Access**: `/admin`  
**Password**: `snappy2025` (change in production!)

The admin dashboard shows:
- Website analytics (placeholder data)
- Form submissions from Support page
- Top visited pages
- Traffic trends

**Production TODO**:
- Replace simple password with proper authentication (JWT, OAuth)
- Connect to real analytics API (Google Analytics, Plausible, etc.)
- Fetch form submissions from Google Sheets API
- Add export functionality for reports

## 📝 Content Updates

### To Update Pricing
Edit `src/pages/Pricing.tsx` → `plans` array

### To Update Contact Info
Edit `src/components/Footer.tsx` and `src/pages/Support.tsx`

### To Update Testimonials
Edit `src/pages/Home.tsx` → `testimonials` array

### To Update Features
Edit `src/pages/Home.tsx` → `features` array

## 🐛 Known Issues

1. **TypeScript Errors Before npm install**: Normal - dependencies not installed yet
2. **Admin Auth**: Simple localStorage-based auth is NOT secure for production
3. **Placeholder Images**: All screenshots need to be replaced with real images
4. **Google Sheets Integration**: Not yet connected (see TODO above)

## 📞 Support

For questions about this website:
- Email: parth@snappy.app
- GitHub: [Your GitHub]

## 📄 License

Copyright © 2025 SNAPPY by Parth Nuwal. All rights reserved.
