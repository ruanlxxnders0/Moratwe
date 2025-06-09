# Logo-Based Theming for Moratwe

This guide explains how to use the automated logo-based theming system that extracts colors from your logo and applies them to your website theme.

## 🎨 What This System Does

The logo-based theming system automatically:
- Extracts dominant colors from your logo image
- Creates a cohesive color palette with primary, secondary, and accent colors
- Applies these colors to your website using CSS custom properties
- Updates your Tailwind CSS configuration dynamically
- Provides a modern, professional design system based on your brand colors

## 📁 Files Added

### CSS Files
- `static/css/logo-theme.css` - Complete theme stylesheet with logo-based color variables
- Enhanced Tailwind configuration in `templates/base.html`

### JavaScript Files
- `static/js/logo-color-extractor.js` - Intelligent color extraction and application

### Templates
- `templates/home-enhanced.html` - Example of the enhanced theme in action
- Updated `templates/base.html` with theme integration

## 🚀 How to Use

### 1. Automatic Setup (Recommended)

The system automatically initializes when your page loads:

1. **Place your logo** at `static/images/logo_transparent.png` (already done)
2. **Load any page** - the system will automatically extract colors
3. **See the preview** - A small preview window will appear showing extracted colors
4. **Copy CSS variables** if you want to customize further

### 2. Manual Color Extraction

You can also manually extract colors using the browser console:

```javascript
// Extract colors from your logo
LogoColorExtractor.init('/static/images/logo_transparent.png').then(result => {
    if (result.success) {
        console.log('Extracted colors:', result.colors);
        // Colors are automatically applied to the theme
    }
});
```

### 3. Custom Logo Path

If your logo is in a different location:

```javascript
LogoColorExtractor.init('/path/to/your/logo.png');
```

## 🎯 Color Variables Available

Once initialized, these CSS custom properties are available:

### Primary Colors
```css
--logo-primary: /* Main brand color */
--logo-primary-light: /* Lighter variant */
--logo-primary-dark: /* Darker variant */
```

### Secondary Colors
```css
--logo-secondary: /* Complementary color */
--logo-secondary-light: /* Lighter variant */
--logo-secondary-dark: /* Darker variant */
```

### Accent Colors
```css
--logo-accent: /* Accent/highlight color */
--logo-accent-light: /* Lighter variant */
--logo-accent-dark: /* Darker variant */
```

### Neutral Palette
```css
--logo-neutral-100: /* Lightest neutral */
--logo-neutral-200: /* ... */
--logo-neutral-900: /* Darkest neutral */
```

## 🎨 Using the Theme Classes

### Button Styles
```html
<button class="btn-logo-primary">Primary Button</button>
<button class="btn-logo-secondary">Secondary Button</button>
<button class="btn-logo-outline">Outline Button</button>
```

### Background Colors
```html
<div class="logo-bg-primary">Primary background</div>
<div class="logo-bg-secondary">Secondary background</div>
<div class="logo-bg-accent">Accent background</div>
```

### Text Colors
```html
<p class="logo-text-primary">Primary text color</p>
<p class="logo-text-secondary">Secondary text color</p>
<p class="logo-text-accent">Accent text color</p>
```

### Card Components
```html
<div class="logo-card">
    <div class="logo-card-header">Card Header</div>
    <div class="p-6">Card content</div>
</div>
```

### Feature Cards
```html
<div class="logo-feature-card">
    <div class="logo-feature-icon">
        <!-- Icon here -->
    </div>
    <h3>Feature Title</h3>
    <p>Feature description</p>
</div>
```

## 🎭 Advanced Customization

### Custom Color Override

If you want to manually set specific colors:

```javascript
// Override extracted colors
document.documentElement.style.setProperty('--logo-primary', '#yourcolor');
document.documentElement.style.setProperty('--logo-secondary', '#yourcolor');
```

### Export Color Palette

Get CSS variables for your extracted colors:

```javascript
const extractor = new LogoColorExtractor();
// After extraction...
const cssVariables = extractor.exportAsCSSVariables(colors);
console.log(cssVariables); // Copy and paste into your CSS
```

## 🌈 Tailwind Integration

The system automatically updates your Tailwind configuration. You can use:

```html
<!-- Tailwind classes that reference logo colors -->
<div class="bg-primary text-white">Primary background</div>
<div class="bg-secondary text-white">Secondary background</div>
<div class="bg-accent text-white">Accent background</div>

<!-- With variants -->
<div class="bg-primary-light">Light primary</div>
<div class="bg-primary-dark">Dark primary</div>
```

## 🔧 Troubleshooting

### Colors Not Extracting?
1. Check that your logo path is correct
2. Ensure the logo is accessible (no CORS issues)
3. Try a different image format (PNG recommended)
4. Check browser console for error messages

### Colors Look Wrong?
1. Use the manual override method to adjust colors
2. Check that your logo has sufficient color contrast
3. Try adjusting the color extraction sensitivity

### Theme Not Applying?
1. Ensure the CSS file is loaded: `static/css/logo-theme.css`
2. Check that the JavaScript file is loaded: `static/js/logo-color-extractor.js`
3. Clear browser cache and reload

## 📱 Responsive Design

All theme components are fully responsive and include:
- Mobile-first design approach
- Flexible grid layouts
- Touch-friendly interactive elements
- Optimized for all screen sizes

## 🌙 Dark Mode Support

The theme includes automatic dark mode support:
- Respects user's system preference
- Automatically adjusts colors for better contrast
- Maintains brand identity in both modes

## 🚀 Performance

The system is optimized for performance:
- Colors are extracted once and cached
- Minimal JavaScript footprint
- CSS custom properties for efficient updates
- No external dependencies

## 📖 Examples

See `templates/home-enhanced.html` for a complete example of the theme in action, including:
- Hero sections with logo-based gradients
- Feature cards with branded colors
- Interactive elements with hover effects
- Responsive design patterns

## 🎉 Next Steps

1. **Test the automatic extraction** - Load your homepage and see the color preview
2. **Customize as needed** - Use the manual override methods for fine-tuning
3. **Apply to other pages** - Use the theme classes throughout your site
4. **Iterate and improve** - Adjust colors based on user feedback and testing

The logo-based theming system will help ensure your website maintains a consistent, professional appearance that perfectly reflects your brand identity! 