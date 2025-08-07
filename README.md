# LiDAR Point Cloud Viewer

A powerful, extensible desktop application for visualizing and analyzing LiDAR point cloud data with a comprehensive plugin system.

![LiDAR Viewer](https://img.shields.io/badge/Python-3.8%2B-blue)
![Qt](https://img.shields.io/badge/GUI-PySide6-green)
![3D](https://img.shields.io/badge/3D-PyVista-orange)

## ✨ Features

### Core Functionality
- **Multi-format Support**: Load LAS/LAZ files with full metadata support
- **Multi-layer Management**: Work with multiple point clouds simultaneously
- **Interactive 3D Visualization**: Real-time navigation with multiple projection modes
- **Advanced Coloring**: Color by elevation, intensity, or custom attributes
- **Point Cloud Filtering**: Spatial, elevation, and attribute-based filtering
- **Layer Management**: Toggle visibility, manage multiple datasets
- **Export Capabilities**: Export filtered data as LAZ files

### 🔌 **Plugin System** (NEW!)
Transform the viewer into a customizable analysis platform:

- **Extensible Architecture**: Add custom tools without modifying core code
- **Multiple Plugin Types**: Analysis, Visualization, Filtering, and Export plugins
- **Hot-swappable**: Enable/disable plugins on-the-fly
- **Built-in Plugin Manager**: Easy plugin management and configuration
- **Developer-Friendly**: Comprehensive API and development tools

### Built-in Analysis Tools
- **Height Profile Analysis**: Create elevation profiles along user-drawn lines
- **Point Cloud Statistics**: Comprehensive statistical analysis with grid-based metrics
- **Advanced Filtering**: Multi-criteria filtering with real-time preview
- **Bounding Box Visualization**: Show layer extents with wireframe boxes
- **Point Picking**: Interactive point selection and information display

### User Interface
- **Dark/Light Themes**: Choose your preferred visual style
- **Dockable Panels**: Customizable workspace layout
- **Status Monitoring**: Real-time feedback on operations
- **Keyboard Shortcuts**: Efficient workflow navigation
- **Responsive Design**: Scales to different screen sizes

## 🚀 Quick Start

### Installation

1. **Prerequisites**:
   ```bash
   pip install PySide6 numpy pyvista matplotlib laspy
   ```

2. **Clone and Run**:
   ```bash
   git clone https://github.com/your-repo/LidarViewer
   cd LidarViewer
   python lidar_viewer.py
   ```

3. **Load Your Data**:
   - Click "Open LAS/LAZ File" or use File → Open
   - Navigate to your point cloud file
   - The viewer will automatically display and analyze your data

### Sample Workflow

1. **Load Point Cloud**: Open your LAS/LAZ file
2. **Explore Data**: Use mouse controls to navigate the 3D view
3. **Analyze**: Enable analysis plugins for statistics and profiling
4. **Filter**: Apply spatial or elevation filters as needed
5. **Export**: Save filtered results for further processing

## 🔌 Plugin System

The plugin system is the viewer's most powerful feature, allowing unlimited customization:

### For Users
- **Plugin Manager**: Access via `Plugins → Plugin Manager`
- **Built-in Plugins**: Statistics, Height Profiles, Advanced Filtering
- **Easy Management**: Enable/disable plugins with a single click
- **No Restart Required**: Plugins load dynamically

### For Developers
- **Simple API**: Clean, documented interfaces for plugin development
- **Template Generator**: Use `plugins/create_plugin.py` to generate plugin templates
- **Multiple Plugin Types**: Choose from Analysis, Visualization, Filter, or Export plugins
- **Rich Documentation**: Complete development guide and examples

### Example Plugin (Point Counter)
```python
from plugins.plugin_manager import BasePlugin, PluginInfo

class PointCounterPlugin(BasePlugin):
    @property
    def info(self) -> PluginInfo:
        return PluginInfo(
            name="Point Counter",
            version="1.0.0",
            author="Your Name",
            description="Count points in selected layer"
        )
    
    def activate(self):
        self.add_toolbar_action("Count", self.count_points)
    
    def count_points(self):
        layer = self.api.get_current_layer()
        if layer:
            count = len(layer.get('points', []))
            self.api.update_status(f"Layer has {count:,} points")
```

## 📁 Project Structure

```
LidarViewer/
├── lidar_viewer.py           # Main application
├── plugins/                  # 🔌 Plugin system
│   ├── plugin_manager.py     # Core plugin framework
│   ├── plugin_dialog.py      # Plugin management UI
│   ├── create_plugin.py      # Plugin template generator
│   ├── built_in/            # Built-in plugins
│   └── user_plugins/        # User-created plugins
├── sidebar/                  # UI controls and layer management
├── viewer/                  # 3D visualization components
├── fileio/                  # File I/O handlers
├── layers/                  # Layer management and database
├── profile_line/            # Height profile analysis
├── point_picking/           # Interactive point selection
└── theme/                   # UI theming system
```

## 🛠️ Development

### Creating Plugins

1. **Use the Generator**:
   ```bash
   cd plugins
   python create_plugin.py
   ```

2. **Follow the Template**:
   - Choose plugin type (Analysis, Visualization, Filter, etc.)
   - Implement required methods
   - Add UI elements as needed

3. **Test Your Plugin**:
   - Restart the viewer
   - Enable plugin in Plugin Manager
   - Test functionality

### Plugin Types Available

- **BasePlugin**: General-purpose plugins with full UI integration
- **AnalysisPlugin**: Data analysis tools with result management
- **VisualizationPlugin**: 3D visualization and rendering effects
- **FilterPlugin**: Data filtering and processing algorithms
- **ExportPlugin**: Custom export/import functionality

### Development Resources

- **Plugin Development Guide**: `PLUGIN_DEVELOPMENT_GUIDE.md`
- **API Documentation**: Inline code documentation
- **Example Plugins**: Working examples in `plugins/built_in/`
- **Template Generator**: `plugins/create_plugin.py`

## 📚 Documentation

- **[Plugin Development Guide](PLUGIN_DEVELOPMENT_GUIDE.md)**: Comprehensive guide for creating plugins
- **[Plugin System Overview](plugins/README.md)**: Overview of the plugin architecture
- **Height Profile Feature**: Detailed analysis of elevation profiles
- **API Reference**: In-code documentation with examples

## 🎯 Use Cases

### Research & Academia
- **Terrain Analysis**: Create height profiles and analyze landscape features
- **Forest Inventory**: Filter and analyze vegetation data
- **Custom Algorithms**: Implement specialized analysis methods as plugins

### Engineering & Surveying
- **Site Analysis**: Comprehensive point cloud statistics and filtering
- **Quality Control**: Validate point cloud data quality
- **Custom Workflows**: Create plugins for specific engineering tasks

### Environmental Monitoring
- **Change Detection**: Compare datasets over time
- **Feature Extraction**: Identify and analyze specific features
- **Data Processing**: Custom filtering and analysis pipelines

## 🔧 Technical Details

### Dependencies
- **Python 3.8+**: Core language
- **PySide6**: Qt-based GUI framework
- **PyVista**: 3D visualization and mesh processing
- **NumPy**: Numerical computing
- **LASPy**: LAS/LAZ file handling
- **Matplotlib**: 2D plotting (for profiles and statistics)

### Performance
- **Efficient Rendering**: Hardware-accelerated 3D visualization
- **Memory Management**: Optimized for large point clouds
- **Multi-threading**: Background processing for complex operations
- **Lazy Loading**: Load data on demand for better responsiveness

### Compatibility
- **File Formats**: LAS 1.2-1.4, LAZ compressed files
- **Platforms**: Windows, macOS, Linux
- **Python Versions**: 3.8, 3.9, 3.10, 3.11, 3.12

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Plugin Development
- Create plugins for specific analysis needs
- Share plugins with the community
- Improve existing plugins

### Core Development
- Bug fixes and performance improvements
- New core features
- Documentation improvements

### Community
- Report issues and bugs
- Suggest new features
- Help other users with questions

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **PyVista**: Excellent 3D visualization capabilities
- **PySide6**: Robust Qt bindings for Python
- **LASPy**: Reliable LAS/LAZ file handling
- **Point Cloud Community**: Inspiration and feedback

## 🔮 Roadmap

### Upcoming Features
- **More Built-in Plugins**: Additional analysis tools
- **Plugin Marketplace**: Share plugins with the community
- **Advanced Visualization**: Enhanced rendering options
- **Batch Processing**: Process multiple files automatically
- **Cloud Integration**: Support for cloud-based point cloud services

### Community Requests
- **Additional File Formats**: Support for more point cloud formats
- **Machine Learning Integration**: ML-powered analysis plugins
- **Web Interface**: Browser-based plugin management
- **Mobile Companion**: Mobile app for field data collection

---

**Transform your point cloud analysis workflow with the power of plugins!**

Whether you're a researcher needing specialized analysis tools, an engineer requiring custom workflows, or a developer wanting to create innovative visualization methods, the LiDAR Viewer's plugin system provides the flexibility and power to meet your needs.
