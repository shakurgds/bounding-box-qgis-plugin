from qgis.PyQt.QtWidgets import (
    QAction, QDialog, QProgressDialog,
    QVBoxLayout, QLabel, QComboBox, QPushButton,
    QDialogButtonBox, QListWidget, QListWidgetItem,
    QCheckBox, QFileDialog, QHBoxLayout, QLineEdit,
    QToolButton, QMenu, QGroupBox
)
from qgis.core import (
    QgsProject, QgsFeature, QgsField, QgsFields,
    QgsGeometry, QgsVectorLayer, QgsWkbTypes,
    QgsMapLayerProxyModel, QgsWkbTypes, QgsVectorFileWriter,
    QgsProcessing, QgsProcessingFeatureSourceDefinition,
    QgsProcessingUtils
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox
from qgis.PyQt.QtCore import QVariant, QObject, Qt
from qgis.PyQt.QtGui import QIcon
import os.path
from processing.tools import *

class FieldSelectorDialog(QDialog):
    def __init__(self, layer, parent=None):
        super().__init__(parent)
        self.layer = layer
        self.setWindowTitle("Select Fields")
        self.setup_ui()
        self.setMinimumWidth(400)
        self.setMinimumHeight(500)
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Field list
        self.field_list = QListWidget()
        self.field_list.setMinimumHeight(300)
        layout.addWidget(self.field_list)
        
        layout.addSpacing(10)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.select_all_btn = QPushButton("Select All")
        self.clear_btn = QPushButton("Clear Selection")
        self.toggle_btn = QPushButton("Toggle Selection")
        
        for btn in [self.select_all_btn, self.clear_btn, self.toggle_btn]:
            btn.setMinimumWidth(100)
            btn.setMinimumHeight(30)
        
        self.select_all_btn.clicked.connect(self.select_all)
        self.clear_btn.clicked.connect(self.clear_selection)
        self.toggle_btn.clicked.connect(self.toggle_selection)
        
        button_layout.addWidget(self.select_all_btn)
        button_layout.addWidget(self.clear_btn)
        button_layout.addWidget(self.toggle_btn)
        
        layout.addLayout(button_layout)
        layout.addSpacing(10)
        
        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        self.setLayout(layout)
        
        if self.layer:
            for field in self.layer.fields():
                item = QListWidgetItem(field.name())
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Unchecked)
                self.field_list.addItem(item)
    
    def select_all(self):
        for i in range(self.field_list.count()):
            self.field_list.item(i).setCheckState(Qt.Checked)
    
    def clear_selection(self):
        for i in range(self.field_list.count()):
            self.field_list.item(i).setCheckState(Qt.Unchecked)
    
    def toggle_selection(self):
        for i in range(self.field_list.count()):
            item = self.field_list.item(i)
            item.setCheckState(Qt.Checked if item.checkState() == Qt.Unchecked else Qt.Unchecked)
    
    def get_selected_fields(self):
        selected = []
        for i in range(self.field_list.count()):
            item = self.field_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

class MBBDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Minimum Bounding Box")
        self.selected_fields = []
        self.setup_ui()
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Layer selection
        layout.addWidget(QLabel("Select Input Layer:"))
        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layer_combo.setMinimumHeight(30)
        layout.addWidget(self.layer_combo)
        
        layout.addSpacing(10)
        
        # Geometry type selection
        layout.addWidget(QLabel("Select Geometry Type:"))
        self.geometry_type = QComboBox()
        self.geometry_type.addItems([
            "Envelope (Bounding Box)",
            "Minimum Oriented Rectangle",
            "Circle",
            "Convex Hull"
        ])
        self.geometry_type.setMinimumHeight(30)
        layout.addWidget(self.geometry_type)
        
        layout.addSpacing(10)
        
        # Grouping options
        group_box = QGroupBox("Grouping Options")
        group_layout = QVBoxLayout()
        
        self.group_check = QCheckBox("Group by field")
        self.group_check.stateChanged.connect(self.toggle_group_field)
        group_layout.addWidget(self.group_check)
        
        self.group_field = QgsFieldComboBox()
        self.group_field.setEnabled(False)
        self.layer_combo.layerChanged.connect(self.group_field.setLayer)
        group_layout.addWidget(self.group_field)
        
        group_box.setLayout(group_layout)
        layout.addWidget(group_box)
        
        layout.addSpacing(10)
        
        # Field selection button
        field_layout = QHBoxLayout()
        field_layout.setSpacing(10)
        self.field_label = QLabel("Selected Fields: 0")
        self.field_button = QToolButton()
        self.field_button.setText("...")
        self.field_button.setMinimumWidth(40)
        self.field_button.setMinimumHeight(30)
        self.field_button.clicked.connect(self.show_field_selector)
        
        field_layout.addWidget(self.field_label)
        field_layout.addWidget(self.field_button)
        field_layout.addStretch()
        layout.addLayout(field_layout)
        
        layout.addSpacing(10)
        
        # Output options
        output_layout = QHBoxLayout()
        output_layout.setSpacing(10)
        layout.addWidget(QLabel("Output (leave empty for memory layer):"))
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Layer name or file path...")
        self.output_path.setMinimumHeight(30)
        output_layout.addWidget(self.output_path)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.setMinimumWidth(80)
        self.browse_button.setMinimumHeight(30)
        self.browse_button.clicked.connect(self.browse_output)
        output_layout.addWidget(self.browse_button)
        layout.addLayout(output_layout)
        
        layout.addSpacing(20)
        
        # OK/Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        for button in self.button_box.buttons():
            button.setMinimumWidth(80)
            button.setMinimumHeight(30)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        self.setLayout(layout)
        
        # Initialize fields
        self.update_fields()

    def toggle_group_field(self, state):
        self.group_field.setEnabled(bool(state))

    def browse_output(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Output Layer",
            "",
            "GeoPackage (*.gpkg);;Shapefile (*.shp)"
        )
        if file_path:
            self.output_path.setText(file_path)

    def update_fields(self):
        self.selected_fields = []
        self.field_label.setText("Selected Fields: 0")

    def show_field_selector(self):
        layer = self.layer_combo.currentLayer()
        if not layer:
            return
            
        dialog = FieldSelectorDialog(layer, self)
        if dialog.exec_():
            self.selected_fields = dialog.get_selected_fields()
            self.field_label.setText(f"Selected Fields: {len(self.selected_fields)}")
    
    def get_selected_fields(self):
        return self.selected_fields
        
    def get_output_info(self):
        path = self.output_path.text().strip()
        if path.lower().endswith(('.gpkg', '.shp')):
            return True, path
        return False, path or "Minimum_Bounding_Box"

class MinimumBoundingBox(QObject):
    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.actions = []
        self.menu = 'Minimum Bounding Box'
        self.plugin_dir = os.path.dirname(__file__)

    def initGui(self):
        icon_path = os.path.join(self.plugin_dir, 'Icon.png')
        self.action = QAction(
            QIcon(icon_path),
            "Create Minimum Bounding Box", 
            self.iface.mainWindow()
        )
        self.action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.menu, self.action)
        self.iface.addToolBarIcon(self.action)
        self.actions.append(self.action)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        self.actions = []

    def run(self):
        dialog = MBBDialog(self.iface.mainWindow())
        
        if not dialog.exec_():
            return
            
        # Get selected options
        layer = dialog.layer_combo.currentLayer()
        selected_fields = dialog.get_selected_fields()
        is_file, output = dialog.get_output_info()
        geometry_type = dialog.geometry_type.currentIndex()
        group_by_enabled = dialog.group_check.isChecked()
        group_field = dialog.group_field.currentField() if group_by_enabled else None
        
        if not layer:
            self.show_error("No layer selected")
            return

        try:
            # Configure fields
            fields = QgsFields()
            
            # Add extent fields
            fields.append(QgsField("min_x", QVariant.Double))
            fields.append(QgsField("min_y", QVariant.Double))
            fields.append(QgsField("max_x", QVariant.Double))
            fields.append(QgsField("max_y", QVariant.Double))
            fields.append(QgsField("extent", QVariant.String))
            
            # Add group field if grouping is enabled
            if group_by_enabled:
                group_field_def = layer.fields().field(group_field)
                fields.append(QgsField(group_field, group_field_def.type()))
            
            # Add selected attribute fields
            if selected_fields:
                for field_name in selected_fields:
                    field = layer.fields().field(field_name)
                    fields.append(QgsField(field_name, field.type()))

            # Create output layer
            if is_file:
                writer_options = QgsVectorFileWriter.SaveVectorOptions()
                writer_options.driverName = "GPKG" if output.lower().endswith('.gpkg') else "ESRI Shapefile"
                transform_context = QgsProject.instance().transformContext()
                
                try:
                    writer = QgsVectorFileWriter.create(
                        output,
                        fields,
                        QgsWkbTypes.Polygon,
                        layer.crs(),
                        transform_context,
                        writer_options
                    )
                    
                    # Process features
                    self.process_features(
                        layer, writer, fields, geometry_type,
                        group_by_enabled, group_field, selected_fields
                    )
                    
                    del writer
                    
                    # Load the saved file
                    saved_layer = QgsVectorLayer(output, output.split('/')[-1].split('.')[0], "ogr")
                    if saved_layer.isValid():
                        QgsProject.instance().addMapLayer(saved_layer)
                    else:
                        self.show_error("Failed to load the saved layer")
                        return
                        
                except Exception as e:
                    self.show_error(f"Error creating output file: {str(e)}")
                    return
            else:
                # Create memory layer
                new_layer = QgsVectorLayer(
                    f"Polygon?crs={layer.crs().authid()}",
                    output,
                    "memory"
                )
                new_layer.dataProvider().addAttributes(fields)
                new_layer.updateFields()
                
                # Process features
                success = self.process_features(
                    layer, new_layer, fields, geometry_type,
                    group_by_enabled, group_field, selected_fields
                )
                
                if not success:
                    return
                    
                QgsProject.instance().addMapLayer(new_layer)

            self.iface.messageBar().pushMessage(
                "Success",
                "Minimum bounding geometries created successfully",
                level=0,
                duration=5
            )
            
        except Exception as e:
            self.show_error(f"Unexpected error: {str(e)}")

    def get_geometry_measurements(self, geom):
        """Calculate measurements for the geometry"""
        bbox = geom.boundingBox()
        width = bbox.width()
        height = bbox.height()
        area = geom.area()
        perimeter = geom.length()
        angle = 0  # Default for regular bounding box
        
        # For oriented bounding box, calculate actual width, height, and angle
        if hasattr(geom, 'orientedMinimumBoundingBox'):
            oriented_result = geom.orientedMinimumBoundingBox()
            if oriented_result:
                oriented_geom, width, height, angle = oriented_result
        
        return {
            'min_x': bbox.xMinimum(),
            'min_y': bbox.yMinimum(),
            'max_x': bbox.xMaximum(),
            'max_y': bbox.yMaximum(),
            'extent': bbox.toString(),
            'width': width,
            'height': height,
            'angle': angle,
            'area': area,
            'perimeter': perimeter
        }

    def process_features(self, layer, output_layer, fields, geometry_type, 
                        group_by_enabled, group_field, selected_fields):
        try:
            # Setup progress
            feature_count = layer.featureCount()
            progress = QProgressDialog(
                "Creating minimum bounding geometries...",
                "Cancel",
                0,
                feature_count,
                self.iface.mainWindow()
            )
            progress.setWindowModality(Qt.WindowModal)

            if group_by_enabled:
                # Group features by field
                groups = {}
                for current, f in enumerate(layer.getFeatures()):
                    if progress.wasCanceled():
                        return False
                    
                    progress.setValue(current)
                    
                    group_val = f[group_field]
                    if group_val not in groups:
                        groups[group_val] = []
                    groups[group_val].append(f)

                # Process each group
                for group_val, features in groups.items():
                    geom = self.create_bounding_geometry(features, geometry_type)
                    if not geom:
                        continue
                        
                    new_feat = QgsFeature(fields)
                    new_feat.setGeometry(geom)
                    
                    # Get extent information
                    bbox = geom.boundingBox()
                    
                    # Set attributes
                    attributes = [
                        bbox.xMinimum(),
                        bbox.yMinimum(),
                        bbox.xMaximum(),
                        bbox.yMaximum(),
                        bbox.toString()
                    ]
                    
                    # Add group value
                    attributes.append(group_val)
                    
                    # Add selected fields
                    if selected_fields:
                        attributes.extend([features[0][field] for field in selected_fields])
                    
                    new_feat.setAttributes(attributes)
                    
                    if isinstance(output_layer, QgsVectorFileWriter):
                        output_layer.addFeature(new_feat)
                    else:
                        output_layer.dataProvider().addFeature(new_feat)
            else:
                # Process each feature individually
                for current, feature in enumerate(layer.getFeatures()):
                    if progress.wasCanceled():
                        return False
                    
                    progress.setValue(current)
                    
                    # Create bounding geometry for single feature
                    geom = self.create_bounding_geometry([feature], geometry_type)
                    if not geom:
                        continue
                    
                    new_feat = QgsFeature(fields)
                    new_feat.setGeometry(geom)
                    
                    # Get extent information
                    bbox = geom.boundingBox()
                    
                    # Set attributes
                    attributes = [
                        bbox.xMinimum(),
                        bbox.yMinimum(),
                        bbox.xMaximum(),
                        bbox.yMaximum(),
                        bbox.toString()
                    ]
                    
                    # Add selected fields
                    if selected_fields:
                        attributes.extend([feature[field] for field in selected_fields])
                    
                    new_feat.setAttributes(attributes)
                    
                    if isinstance(output_layer, QgsVectorFileWriter):
                        output_layer.addFeature(new_feat)
                    else:
                        output_layer.dataProvider().addFeature(new_feat)

            progress.setValue(feature_count)
            return True
            
        except Exception as e:
            self.show_error(f"Error processing features: {str(e)}")
            return False

    def create_bounding_geometry(self, features, geometry_type):
        # Combine all geometries
        geometries = [f.geometry() for f in features]
        combined = QgsGeometry.unaryUnion(geometries)
        
        if not combined:
            return None
            
        if geometry_type == 0:  # Envelope
            return QgsGeometry.fromRect(combined.boundingBox())
        elif geometry_type == 1:  # Oriented rectangle
            return combined.orientedMinimumBoundingBox()
        elif geometry_type == 2:  # Circle
            return combined.boundingCircle()
        elif geometry_type == 3:  # Convex hull
            return combined.convexHull()
        
        return None

    def show_error(self, message):
        self.iface.messageBar().pushMessage(
            "Error",
            message,
            level=2,
            duration=5
        ) 