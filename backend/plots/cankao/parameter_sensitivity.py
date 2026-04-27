import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from scipy.io import loadmat, savemat
from scipy.interpolate import griddata
import os

def load_mat_data(mat_file):
    """
    Load data from a .mat file and extract gamma, delta, and metrics
    Data is extracted from the .mat file with the following column structure:
    Column 15: gamma values
    Column 16: delta values
    Column 17: neg_log_pvalue
    Column 18: enrichment_count
    """
    try:
        # Load the .mat file
        print(f"Loading data from: {os.path.abspath(mat_file)}")
        mat_data = loadmat(mat_file)
        
        # Extract the data array (assuming it's the first variable in the .mat file)
        data_key = [k for k in mat_data.keys() if not k.startswith('__')][0]
        data_array = mat_data[data_key]
        
        # Extract all values at once using array slicing
        # Each row represents a different configuration
        gamma = data_array[:, 14]      # Column 15: gamma
        delta = data_array[:, 15]      # Column 16: delta
        neg_log_pvalue = data_array[:, 16]  # Column 17: neg_log_pvalue
        enrichment_count = data_array[:, 17]  # Column 18: enrichment_count
        
        print(f"Loaded {len(gamma)} data points")
        print(f"Gamma range: {gamma.min():.2e} to {gamma.max():.2e}")
        print(f"Delta range: {delta.min():.2e} to {delta.max():.2e}")
        
        return gamma, delta, neg_log_pvalue, enrichment_count
        
    except Exception as e:
        print(f"Error loading {mat_file}: {str(e)}")
        raise

def create_3d_sensitivity_plot(gamma, delta, metric1, metric2, 
                             metric1_name='neg_log_pvalue',
                             metric2_name='enrichment_count',
                             output_file='parameter_sensitivity.png'):
    # Set global font settings
    plt.rcParams['font.family'] = 'Times New Roman'
    plt.rcParams['font.weight'] = 'bold'
    plt.rcParams['axes.labelweight'] = 'bold'
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['font.size'] = 16
    """
    Create a 3D surface plot showing two metrics on the same plot
    """
    # Convert to numpy arrays if they're not already
    gamma = np.asarray(gamma)
    delta = np.asarray(delta)
    metric1 = np.asarray(metric1)
    metric2 = np.asarray(metric2)
    
    # Get unique and sorted gamma and delta values
    unique_gamma = np.unique(gamma)
    unique_delta = np.unique(delta)
    
    # Create a grid of unique gamma and delta values
    X, Y = np.meshgrid(unique_gamma, unique_delta)
    
    # Create empty arrays for the metrics
    Z1 = np.full_like(X, np.nan, dtype=float)
    Z2 = np.full_like(X, np.nan, dtype=float)
    
    # Fill in the metrics for each (gamma, delta) pair
    for i, g in enumerate(unique_gamma):
        for j, d in enumerate(unique_delta):
            # Find indices where both gamma and delta match (with floating point tolerance)
            mask = (np.abs(gamma - g) < 1e-10) & (np.abs(delta - d) < 1e-10)
            if np.any(mask):
                # Use the first matching value if there are multiple
                Z1[j, i] = metric1[mask][0] if not np.isnan(metric1[mask][0]) else np.nan
                Z2[j, i] = metric2[mask][0] if not np.isnan(metric2[mask][0]) else np.nan
    
    # Create figure with adjusted size for better z-label visibility
    fig = plt.figure(figsize=(14, 8))  # Wider figure to ensure z-label is visible
    ax1 = fig.add_subplot(111, projection='3d')
    
    # Create custom colormaps
    from matplotlib.colors import LinearSegmentedColormap
    
    # Create a more subtle colormap (muted blue to purple)
    colors = [(0.8, 0.9, 0.9),  # Very light teal
              (0.7, 0.85, 0.9),  # Light blue
              (0.8, 0.7, 0.9),   # Light purple
              (0.9, 0.7, 0.8)]   # Light pink
    cmap = LinearSegmentedColormap.from_list('custom_teal_purple', colors, N=256)
    
    # Create a finer grid for smooth interpolation
    from scipy import interpolate
    
    # Get valid points (non-NaN)
    valid_mask = ~np.isnan(Z1)
    X_valid = np.log10(X[valid_mask])
    Y_valid = np.log10(Y[valid_mask])
    Z1_valid = Z1[valid_mask]
    
    # Create a finer grid
    x_min, x_max = np.log10(unique_gamma).min(), np.log10(unique_gamma).max()
    y_min, y_max = np.log10(unique_delta).min(), np.log10(unique_delta).max()
    
    # Add some padding to the grid
    x_pad = 0.1 * (x_max - x_min)
    y_pad = 0.1 * (y_max - y_min)
    
    x_fine = np.linspace(x_min - x_pad, x_max + x_pad, 50)
    y_fine = np.linspace(y_min - y_pad, y_max + y_pad, 50)
    X_fine, Y_fine = np.meshgrid(x_fine, y_fine)
    
    # Interpolate Z values on the finer grid
    if len(X_valid) > 0:
        # Use RBF interpolation for better handling of scattered data
        try:
            from scipy.interpolate import Rbf
            rbf = Rbf(X_valid, Y_valid, Z1_valid, function='thin_plate', smooth=0.1)
            Z1_fine = rbf(X_fine, Y_fine)
        except:
            # Fall back to linear interpolation if RBF fails
            Z1_fine = interpolate.griddata(
                np.column_stack((X_valid, Y_valid)),
                Z1_valid,
                (X_fine, Y_fine),
                method='linear',
                fill_value=np.nan
            )
            
            # Fill remaining NaNs with nearest neighbor
            if np.isnan(Z1_fine).any():
                Z1_fine = interpolate.griddata(
                    np.column_stack((X_valid, Y_valid)),
                    Z1_valid,
                    (X_fine, Y_fine),
                    method='nearest'
                )
    else:
        Z1_fine = np.zeros_like(X_fine)
    
    # Calculate vmin and vmax, ensuring they're finite
    z_min = np.nanmin(Z1) if not np.all(np.isnan(Z1)) else 0
    z_max = np.nanmax(Z1) if not np.all(np.isnan(Z1)) else 1
    
    # If all values are the same, add a small range to avoid errors
    if z_min == z_max:
        z_min -= 0.1
        z_max += 0.1
    
    # Plot the surface
    if np.all(np.isnan(Z1_fine)):
        Z1_fine = np.zeros_like(X_fine)
        
    surf = ax1.plot_surface(X_fine, Y_fine, np.nan_to_num(Z1_fine, nan=0), 
                          cmap=cmap, alpha=0.9, 
                          vmin=z_min, vmax=z_max,
                          linewidth=0.5, antialiased=True,
                          rstride=1, cstride=1,
                          shade=True, edgecolor='#666666')
    
    # Set axis labels with proper formatting
    ax1.set_xlabel('gamma', fontsize=16, labelpad=10, fontweight='bold')
    ax1.set_ylabel('delta', fontsize=16, labelpad=10, fontweight='bold')
    ax1.set_zlabel('$-\log_{10}(p)$', fontsize=16, labelpad=15, rotation=90, fontweight='bold')
    ax1.zaxis.set_rotate_label(False)  # Keep label horizontal
    
    # Adjust the 3D pane to make more room for the z-label
    ax1.set_box_aspect([1, 1, 0.8])  # Adjust the aspect ratio of the 3D plot
    
    # Adjust margins to make more room for z-label
    plt.subplots_adjust(left=0.25, right=0.9, bottom=0.1, top=0.9)
    
    # Position z-label properly
    ax1.zaxis.set_rotate_label(True)
    ax1.set_zlabel('$-\\log_{10}(p)$', fontsize=12, labelpad=20)
    ax1.zaxis.set_label_coords(0, 0.5)
    
    # Set custom tick labels for log scale
    ticks = [-3, -2, -1, 0, 1, 2, 3]
    tick_labels = ['1e-3', '1e-2', '1e-1', '1', '1e1', '1e2', '1e3']
    
    ax1.set_xticks(ticks)
    ax1.set_xticklabels(tick_labels, fontsize=14, fontweight='bold')
    ax1.set_yticks(ticks)
    ax1.set_yticklabels(tick_labels, fontsize=14, fontweight='bold')
    ax1.tick_params(axis='z', which='major', labelsize=14, pad=8)
    
    # Set z-axis tick labels
    z_ticks = ax1.get_zticks()
    ax1.set_zticklabels([f'{tick:.1f}' for tick in z_ticks], fontsize=14, fontweight='bold')
    
    # Set z-axis limits from 0 to next highest integer
    z_max = np.nanmax(Z1)
    z_ceil = np.ceil(z_max) if z_max > 0 else 1.0  # Ensure at least 0-1 range
    ax1.set_zlim(0, z_ceil)
    
    # Adjust z-ticks for better readability
    ax1.zaxis.set_major_formatter(plt.ScalarFormatter(useMathText=True))
    

    
    # Set the 3D view angle
    ax1.view_init(elev=30, azim=60)
    
    # Add grid with custom styling
    ax1.grid(True, linestyle='--', alpha=0.3)
    
    # Subtle lighting for a softer look
    from matplotlib.colors import LightSource
    ls = LightSource(azdeg=135, altdeg=30)
    
    # Use softer lighting with lower contrast
    if not np.all(np.isnan(Z1_fine)):
        rgb = ls.shade(np.nan_to_num(Z1_fine, nan=0), cmap=cmap, 
                      vert_exag=0.1,  # Reduced vertical exaggeration
                      blend_mode='hsv',  # Softer blend mode
                      dx=0.3, dy=0.3,   # Smaller light spread
                      fraction=0.8)      # Reduced light intensity
        surf.set_facecolor(rgb.reshape(-1, 4))
    
    # Add legend for the max value marker
    # Remove the empty legend
    if ax1.get_legend() is not None:
        ax1.get_legend().remove()
    
    # Adjust layout with more left padding for z-label
    plt.tight_layout(rect=[0.25, 0, 0.95, 0.95])  # Increased left padding to 0.25
    
    # Save figure as PNG and PDF with 600 DPI
    base_filename = os.path.splitext(output_file)[0]  # Remove extension if present
    png_file = f"{base_filename}.png"
    pdf_file = f"{base_filename}.pdf"
    
    # Save as PNG
    plt.savefig(png_file, dpi=600, bbox_inches='tight')
    # Save as PDF (vector format, DPI doesn't apply but we keep the parameter for consistency)
    plt.savefig(pdf_file, dpi=600, bbox_inches='tight')
    
    print(f"Plots saved as {os.path.abspath(png_file)}")
    print(f"and {os.path.abspath(pdf_file)}")
    
    return fig, ax1

def main():
    # List of cancer types to process
    cancer_types = ['BRCA', 'BLCA', 'KIRC', 'LUAD', 'SKCM', 'STAD', 'UCEC', 'UVM']
    
    # Create output directory if it doesn't exist
    os.makedirs('./param_sensitivity', exist_ok=True)
    
    for cancer_type in cancer_types:
        try:
            print(f"\nProcessing {cancer_type}...")
            # Configuration
            mat_file = f'./mat_results/参数敏感性1e-3 - 1e3/{cancer_type}_results.mat'
            output_plot = f'./param_sensitivity/ps_{cancer_type}'  # No extension here, will be added in savefig
            
            # Load data from the .mat file
            gamma, delta, neg_log_pvalue, enrichment_count = load_mat_data(mat_file)
            
            # Create and save plot
            create_3d_sensitivity_plot(
                gamma, delta, 
                neg_log_pvalue, enrichment_count,
                metric1_name='neg_log_pvalue',
                metric2_name='enrichment_count',
                output_file=output_plot
            )
            print(f"Successfully created plot: {os.path.abspath(output_plot)}")
            
        except Exception as e:
            print(f"Error processing {cancer_type}: {str(e)}")
            continue  # Continue with next cancer type if error occurs

if __name__ == "__main__":
    main()
