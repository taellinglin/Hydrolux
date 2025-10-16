import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

# Create figure with dark cosmic background
fig, ax = plt.subplots(1, 1, figsize=(14, 8))
fig.patch.set_facecolor('black')
ax.set_facecolor('black')

# Remove axes
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.axis('off')

# Add title
title = ax.text(0.5, 0.9, 'Cosmic Balance: Light ↔ Mass', 
                fontsize=24, color='white', ha='center',
                fontfamily='serif', fontweight='bold')

# Create the main equation text
equation_left = r'$\bigstar \Phi_{\mathrm{light}} = M_{\mathrm{fragments}}$'

# Add left equation (normal)
left_text = ax.text(0.25, 0.5, equation_left, 
                   fontsize=32, color='cyan', ha='center', va='center',
                   fontfamily='serif', fontweight='bold')

# Add right equation (mirrored)
# We create a transformed version for the mirror effect
right_text = ax.text(0.75, 0.5, equation_left, 
                    fontsize=32, color='orange', ha='center', va='center',
                    fontfamily='serif', fontweight='bold',
                    rotation=0)  # No rotation, we'll handle mirroring differently

# For mirroring effect, we'll create a reflected version
# Since matplotlib doesn't have direct mirroring, we'll create a custom solution
ax.text(0.75, 0.5, equation_left, 
        fontsize=32, color='orange', ha='center', va='center',
        fontfamily='serif', fontweight='bold',
        transform=ax.transData + plt.matplotlib.transforms.Affine2D().scale(-1, 1).translate(1.5, 0))

# Add mirror line (cosmic gateway)
mirror_line = plt.Line2D([0.5, 0.5], [0.3, 0.7], color='white', linewidth=3, alpha=0.7)
ax.add_line(mirror_line)

# Add shimmer effect around mirror line
for i in range(5):
    offset = (i-2) * 0.005
    shimmer_line = plt.Line2D([0.5+offset, 0.5+offset], [0.3, 0.7], 
                             color='yellow', linewidth=1, alpha=0.3)
    ax.add_line(shimmer_line)

# Add cosmic particles (light on left, matter on right)
np.random.seed(42)  # For reproducible random positions

# Light particles (left side - cyan)
for _ in range(30):
    x = np.random.uniform(0.1, 0.45)
    y = np.random.uniform(0.2, 0.8)
    size = np.random.uniform(20, 100)
    alpha = np.random.uniform(0.3, 0.8)
    ax.scatter(x, y, s=size, color='cyan', alpha=alpha, marker='*')

# Matter fragments (right side - orange/red)
for _ in range(25):
    x = np.random.uniform(0.55, 0.9)
    y = np.random.uniform(0.2, 0.8)
    size = np.random.uniform(30, 80)
    alpha = np.random.uniform(0.4, 0.7)
    ax.scatter(x, y, s=size, color='orange', alpha=alpha, marker='o')

# Add some connecting lines to show balance
for i in range(8):
    y = 0.3 + i * 0.05
    balance_line = plt.Line2D([0.48, 0.52], [y, y], 
                             color='white', linewidth=1, alpha=0.2, linestyle='--')
    ax.add_line(balance_line)

# Add explanatory text
explanation = ax.text(0.5, 0.15, 
                     'The Sum of All Light = The Mass of All Fragments',
                     fontsize=16, color='white', ha='center',
                     fontfamily='serif', fontstyle='italic')

# Add subtle grid for cosmic feel
ax.grid(True, alpha=0.1, color='white', linestyle='-')
ax.set_axisbelow(True)

plt.tight_layout()
plt.show()

# Alternative version that saves to file
def create_high_quality_version():
    """Create a higher quality version and save to file"""
    fig, ax = plt.subplots(1, 1, figsize=(16, 10))
    fig.patch.set_facecolor('black')
    ax.set_facecolor('black')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis('off')
    
    # Add stars in background
    for _ in range(100):
        x = np.random.uniform(0, 1)
        y = np.random.uniform(0, 1)
        size = np.random.uniform(1, 3)
        ax.scatter(x, y, s=size, color='white', alpha=0.5)
    
    # Title
    ax.text(0.5, 0.9, 'Cosmic Balance: Light ↔ Mass', 
            fontsize=28, color='white', ha='center',
            fontfamily='serif', fontweight='bold')
    
    # Equations
    eq_left = ax.text(0.25, 0.5, equation_left, 
                     fontsize=36, color='cyan', ha='center', va='center',
                     fontfamily='serif', fontweight='bold')
    
    # Mirror line with glow
    for width, alpha in [(8, 0.3), (5, 0.5), (2, 0.8)]:
        mirror = plt.Line2D([0.5, 0.5], [0.3, 0.7], color='yellow', 
                           linewidth=width, alpha=alpha)
        ax.add_line(mirror)
    
    # Save high quality version
    plt.savefig('cosmic_balance_equation.png', dpi=300, bbox_inches='tight', 
                facecolor='black', edgecolor='none')
    plt.close()
    print("High-quality version saved as 'cosmic_balance_equation.png'")

# Uncomment the line below to create and save a high-quality version
# create_high_quality_version()