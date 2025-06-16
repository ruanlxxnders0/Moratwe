// Logo Color Extractor for Moratwe Theme
// This script helps extract colors from your logo and apply them to the theme

class LogoColorExtractor {
    constructor() {
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.colors = [];
    }

    // Load and analyze logo image
    async extractColorsFromLogo(logoPath) {
        return new Promise((resolve, reject) => {
            const img = new Image();
            img.crossOrigin = 'anonymous';
            
            img.onload = () => {
                this.canvas.width = img.width;
                this.canvas.height = img.height;
                this.ctx.drawImage(img, 0, 0);
                
                const colors = this.analyzeImageColors();
                this.applyColorsToTheme(colors);
                resolve(colors);
            };
            
            img.onerror = () => reject(new Error('Failed to load logo'));
            img.src = logoPath;
        });
    }

    // Analyze image and extract dominant colors
    analyzeImageColors() {
        const imageData = this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height);
        const data = imageData.data;
        const colorCounts = {};
        
        // Sample every 4th pixel for performance
        for (let i = 0; i < data.length; i += 16) {
            const r = data[i];
            const g = data[i + 1];
            const b = data[i + 2];
            const a = data[i + 3];
            
            // Skip transparent pixels
            if (a < 128) continue;
            
            // Convert to hex for easier processing
            const hex = this.rgbToHex(r, g, b);
            colorCounts[hex] = (colorCounts[hex] || 0) + 1;
        }
        
        // Sort by frequency and get top colors
        const sortedColors = Object.entries(colorCounts)
            .sort(([,a], [,b]) => b - a)
            .slice(0, 10)
            .map(([color]) => color);
        
        return this.processExtractedColors(sortedColors);
    }

    // Process and categorize extracted colors
    processExtractedColors(colors) {
        const processedColors = {
            primary: null,
            secondary: null,
            accent: null,
            neutrals: []
        };
        
        // Filter out very light/dark colors for primary selection
        const candidateColors = colors.filter(color => {
            const { h, s, l } = this.hexToHsl(color);
            return l > 0.2 && l < 0.8 && s > 0.3; // Good saturation and lightness
        });
        
        if (candidateColors.length > 0) {
            processedColors.primary = candidateColors[0];
            
            // Find complementary colors
            if (candidateColors.length > 1) {
                processedColors.secondary = this.findComplementaryColor(candidateColors);
            }
            
            if (candidateColors.length > 2) {
                processedColors.accent = candidateColors[2];
            }
        }
        
        // Extract neutral colors
        processedColors.neutrals = colors.filter(color => {
            const { s } = this.hexToHsl(color);
            return s < 0.2; // Low saturation colors
        }).slice(0, 3);
        
        return processedColors;
    }

    // Find a complementary color from the extracted colors
    findComplementaryColor(colors) {
        if (colors.length < 2) return colors[1] || colors[0];
        
        const primaryHsl = this.hexToHsl(colors[0]);
        let bestMatch = colors[1];
        let maxDistance = 0;
        
        for (let i = 1; i < colors.length; i++) {
            const colorHsl = this.hexToHsl(colors[i]);
            const hueDistance = Math.abs(primaryHsl.h - colorHsl.h);
            const distance = Math.min(hueDistance, 360 - hueDistance);
            
            if (distance > maxDistance) {
                maxDistance = distance;
                bestMatch = colors[i];
            }
        }
        
        return bestMatch;
    }

    // Apply extracted colors to CSS custom properties
    applyColorsToTheme(colors) {
        const root = document.documentElement;
        
        if (colors.primary) {
            root.style.setProperty('--logo-primary', colors.primary);
            root.style.setProperty('--logo-primary-light', this.lightenColor(colors.primary, 20));
            root.style.setProperty('--logo-primary-dark', this.darkenColor(colors.primary, 20));
        }
        
        if (colors.secondary) {
            root.style.setProperty('--logo-secondary', colors.secondary);
            root.style.setProperty('--logo-secondary-light', this.lightenColor(colors.secondary, 20));
            root.style.setProperty('--logo-secondary-dark', this.darkenColor(colors.secondary, 20));
        }
        
        if (colors.accent) {
            root.style.setProperty('--logo-accent', colors.accent);
            root.style.setProperty('--logo-accent-light', this.lightenColor(colors.accent, 20));
            root.style.setProperty('--logo-accent-dark', this.darkenColor(colors.accent, 20));
        }
        
        // Update Tailwind config if available
        this.updateTailwindConfig(colors);
        
        // Trigger theme update event
        document.dispatchEvent(new CustomEvent('logoThemeUpdated', { detail: colors }));
    }

    // Update Tailwind configuration
    updateTailwindConfig(colors) {
        if (typeof tailwind !== 'undefined' && tailwind.config) {
            const newConfig = {
                theme: {
                    extend: {
                        colors: {
                            primary: {
                                light: colors.primary ? this.lightenColor(colors.primary, 20) : '#8e68ff',
                                DEFAULT: colors.primary || '#6941e1',
                                dark: colors.primary ? this.darkenColor(colors.primary, 20) : '#5832c2',
                            },
                            secondary: {
                                light: colors.secondary ? this.lightenColor(colors.secondary, 20) : '#5ecdd8',
                                DEFAULT: colors.secondary || '#36bbc8',
                                dark: colors.secondary ? this.darkenColor(colors.secondary, 20) : '#2a9ca8',
                            },
                            accent: {
                                light: colors.accent ? this.lightenColor(colors.accent, 20) : '#ffd876',
                                DEFAULT: colors.accent || '#ffc82c',
                                dark: colors.accent ? this.darkenColor(colors.accent, 20) : '#e0a800',
                            }
                        },
                        fontFamily: {
                            'poppins': ['Poppins', 'sans-serif'],
                        }
                    }
                }
            };
            
            // Update Tailwind config
            tailwind.config = newConfig;
        }
    }

    // Utility functions for color manipulation
    rgbToHex(r, g, b) {
        return "#" + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1);
    }

    hexToHsl(hex) {
        const r = parseInt(hex.slice(1, 3), 16) / 255;
        const g = parseInt(hex.slice(3, 5), 16) / 255;
        const b = parseInt(hex.slice(5, 7), 16) / 255;

        const max = Math.max(r, g, b);
        const min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;

        if (max === min) {
            h = s = 0;
        } else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = (g - b) / d + (g < b ? 6 : 0); break;
                case g: h = (b - r) / d + 2; break;
                case b: h = (r - g) / d + 4; break;
            }
            h /= 6;
        }

        return { h: h * 360, s, l };
    }

    lightenColor(hex, percent) {
        const { h, s, l } = this.hexToHsl(hex);
        const newL = Math.min(1, l + (percent / 100));
        return this.hslToHex(h, s, newL);
    }

    darkenColor(hex, percent) {
        const { h, s, l } = this.hexToHsl(hex);
        const newL = Math.max(0, l - (percent / 100));
        return this.hslToHex(h, s, newL);
    }

    hslToHex(h, s, l) {
        h /= 360;
        const hue2rgb = (p, q, t) => {
            if (t < 0) t += 1;
            if (t > 1) t -= 1;
            if (t < 1/6) return p + (q - p) * 6 * t;
            if (t < 1/2) return q;
            if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
            return p;
        };

        let r, g, b;
        if (s === 0) {
            r = g = b = l;
        } else {
            const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
            const p = 2 * l - q;
            r = hue2rgb(p, q, h + 1/3);
            g = hue2rgb(p, q, h);
            b = hue2rgb(p, q, h - 1/3);
        }

        const toHex = (c) => {
            const hex = Math.round(c * 255).toString(16);
            return hex.length === 1 ? '0' + hex : hex;
        };

        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    }

    // Generate a complete color palette from extracted colors
    generateColorPalette(baseColors) {
        const palette = {
            primary: baseColors.primary || '#2D7DD2',
            secondary: baseColors.secondary || '#E67E22',
            accent: baseColors.accent || '#27AE60',
            neutrals: {
                100: '#F8F9FA',
                200: '#E9ECEF',
                300: '#DEE2E6',
                400: '#CED4DA',
                500: '#6C757D',
                600: '#495057',
                700: '#343A40',
                800: '#212529',
                900: '#0D1117'
            },
            semantic: {
                success: baseColors.accent || '#27AE60',
                warning: '#F1C40F',
                error: '#E74C3C',
                info: baseColors.primary || '#2D7DD2'
            }
        };

        return palette;
    }

    // Export colors as CSS variables
    exportAsCSSVariables(colors) {
        const palette = this.generateColorPalette(colors);
        let css = ':root {\n';
        
        css += `  --logo-primary: ${palette.primary};\n`;
        css += `  --logo-primary-light: ${this.lightenColor(palette.primary, 20)};\n`;
        css += `  --logo-primary-dark: ${this.darkenColor(palette.primary, 20)};\n`;
        css += `  --logo-secondary: ${palette.secondary};\n`;
        css += `  --logo-secondary-light: ${this.lightenColor(palette.secondary, 20)};\n`;
        css += `  --logo-secondary-dark: ${this.darkenColor(palette.secondary, 20)};\n`;
        css += `  --logo-accent: ${palette.accent};\n`;
        css += `  --logo-accent-light: ${this.lightenColor(palette.accent, 20)};\n`;
        css += `  --logo-accent-dark: ${this.darkenColor(palette.accent, 20)};\n`;
        
        Object.entries(palette.neutrals).forEach(([key, value]) => {
            css += `  --logo-neutral-${key}: ${value};\n`;
        });
        
        Object.entries(palette.semantic).forEach(([key, value]) => {
            css += `  --logo-${key}: ${value};\n`;
        });
        
        css += '}';
        return css;
    }

    // Initialize the color extractor
    static async init(logoPath = '/static/images/logo_transparent.png') {
        const extractor = new LogoColorExtractor();
        try {
            const colors = await extractor.extractColorsFromLogo(logoPath);
            console.log('Extracted logo colors:', colors);
            
            // Create a preview element to show the extracted colors
            extractor.createColorPreview(colors);
            
            return { success: true, colors, extractor };
        } catch (error) {
            console.error('Failed to extract logo colors:', error);
            return { success: false, error };
        }
    }

    // Create a visual preview of extracted colors
    createColorPreview(colors) {
        const previewId = 'logo-color-preview';
        let preview = document.getElementById(previewId);
        
        if (!preview) {
            preview = document.createElement('div');
            preview.id = previewId;
            preview.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: white;
                padding: 15px;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                z-index: 10000;
                font-family: system-ui, -apple-system, sans-serif;
                max-width: 300px;
                border: 1px solid #e1e5e9;
            `;
            document.body.appendChild(preview);
            
            // Auto-hide after 10 seconds
            setTimeout(() => {
                if (preview.parentNode) {
                    preview.remove();
                }
            }, 10000);
        }
        
        const palette = this.generateColorPalette(colors);
        
        preview.innerHTML = `
            <h3 style="margin: 0 0 10px 0; font-size: 14px; color: #333;">
                Logo Colors Extracted 
                <button onclick="this.parentElement.parentElement.remove()" style="float: right; border: none; background: none; font-size: 16px; cursor: pointer;">×</button>
            </h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 10px;">
                ${Object.entries({
                    Primary: palette.primary,
                    Secondary: palette.secondary,
                    Accent: palette.accent
                }).map(([name, color]) => `
                    <div style="text-align: center;">
                        <div style="width: 40px; height: 40px; background: ${color}; border-radius: 50%; margin: 0 auto 5px; border: 2px solid #f0f0f0;"></div>
                        <div style="font-size: 10px; color: #666;">${name}</div>
                        <div style="font-size: 9px; color: #999; font-family: monospace;">${color}</div>
                    </div>
                `).join('')}
            </div>
            <button onclick="navigator.clipboard.writeText(document.getElementById('css-output').textContent)" 
                    style="width: 100%; padding: 8px; background: ${palette.primary}; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 12px;">
                Copy CSS Variables
            </button>
            <textarea id="css-output" style="width: 100%; height: 60px; margin-top: 8px; font-size: 10px; font-family: monospace; border: 1px solid #ddd; border-radius: 3px; padding: 5px; resize: vertical;">${this.exportAsCSSVariables(colors)}</textarea>
        `;
    }
}

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for other scripts to load
    setTimeout(() => {
        LogoColorExtractor.init().then(result => {
            if (result.success) {
                console.log('✅ Logo theme initialized successfully');
            } else {
                console.log('⚠️ Logo theme initialization failed, using default colors');
            }
        });
    }, 1000);
});

// Export for manual use
window.LogoColorExtractor = LogoColorExtractor; 