import os
import sys
import logging
import tempfile
import ctags
from gi.repository import GObject, GdkPixbuf, Gedit, Gtk

logging.basicConfig()
LOG_LEVEL = logging.WARN

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
ICON_DIR = os.path.join(DATA_DIR, 'icons', '16x16')
 
class SourceTree(Gtk.VBox):
    """
    Source Tree Widget
    
    A treeview storing the heirarchy of source code symbols within a particular
    document. Requries exhuberant-ctags.
    """
    __gsignals__ = {
        "tag-activated": (GObject.SIGNAL_RUN_FIRST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,)),
    }   
    def get_pixbuf(self, icon_name):
        """ 
        Get the pixbuf for a specific icon name fron an internal dictionary of
        pixbufs. If the icon is not already in the dictionary, it will be loaded
        from an external file.        
        """
        if icon_name not in self._pixbufs: 
            filename = os.path.join(ICON_DIR, icon_name + ".png")
            try:
                self._pixbufs[icon_name] = GdkPixbuf.Pixbuf.new_from_file(filename)
            except Exception as e:
                self._log.warn("Could not load pixbuf for icon '%s': %s", 
                               icon_name, 
                               str(e))
                self._pixbufs[icon_name] = GdkPixbuf.Pixbuf.new_from_file(
                                            os.path.join(ICON_DIR, "missing-image.png"))
        return self._pixbufs[icon_name]
         
    def __init__(self):
        Gtk.VBox.__init__(self)
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.setLevel(LOG_LEVEL)
        self._pixbufs = {}
        self.expanded_rows = {}
        
        # preferences (should be set by plugin)
        self.show_line_numbers = True
        self.ctags_executable = 'ctags'
        self.expand_rows = True
        
        self.create_ui()
        self.show_all()
    
    def clear(self):
        """ Clear the tree view so that new data can be loaded. """
        self._store.clear()
        
    def create_ui(self):
        """ Craete the main user interface and pack into box. """
        self._store = Gtk.TreeStore(GdkPixbuf.Pixbuf,       # icon
                                    GObject.TYPE_STRING,    # name
                                    GObject.TYPE_STRING,    # kind
                                    GObject.TYPE_STRING,    # uri 
                                    GObject.TYPE_STRING,    # line               
                                    GObject.TYPE_STRING)    # markup                           
        self._treeview = Gtk.TreeView.new_with_model(self._store)
        self._treeview.set_headers_visible(False)          
        column = Gtk.TreeViewColumn("Symbol")
        cell = Gtk.CellRendererPixbuf()
        column.pack_start(cell, False)
        column.add_attribute(cell, 'pixbuf', 0)
        cell = Gtk.CellRendererText()
        column.pack_start(cell, True)
        column.add_attribute(cell, 'markup', 5)
        
        self._treeview.append_column(column)

        self._treeview.connect("row-activated", self.on_row_activated)
        self._treeview.connect("row-expanded", self.on_row_expanded)
        self._treeview.connect("row-collapsed", self.on_row_collapsed)
        
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self._treeview)
        self.pack_start(sw, True, True, 0)
    
    def _get_tag_iter(self, tag, parent_iter=None):
        """
        Get the tree iter for the specified tag, or None if the tag cannot
        be found.
        """
        tag_iter = self._store.iter_children(parent_iter)
        while tag_iter:
            if self._store.get_value(tag_iter, 1) == tag.name:
                return tag_iter
            tag_iter = self._store.iter_next(tag_iter)
        
        return None
            
    def _get_kind_iter(self, kind, uri, parent_iter=None):
        """
        Get the iter for the specified kind. Creates a new node if the iter
        is not found under the specirfied parent_iter.
        """
        kind_iter = self._store.iter_children(parent_iter)
        while kind_iter:
            if self._store.get_value(kind_iter, 2) == kind.name:
                return kind_iter
            kind_iter = self._store.iter_next(kind_iter)
        
        # Kind node not found, so we'll create it.
        pixbuf = self.get_pixbuf(kind.icon_name())
        markup = "<i>%s</i>" % kind.group_name()
        kind_iter = self._store.append(parent_iter, (pixbuf, 
                                       kind.group_name(), 
                                       kind.name, 
                                       uri, 
                                       None, 
                                       markup))
        return kind_iter
        
    def load(self, kinds, tags, uri):
        """
        Load the tags into the treeview and restore the expanded rows if 
        applicable.
        """
        # load root-level tags first
        for i, tag in enumerate(tags):
            if "class" not in tag.fields: 
                parent_iter = None
                pixbuf = self.get_pixbuf(tag.kind.icon_name())
                if 'line' in tag.fields and self.show_line_numbers:
                    markup = "%s [%s]" % (tag.name, tag.fields['line'])
                else:
                    markup = tag.name
                kind_iter = self._get_kind_iter(tag.kind, uri, parent_iter)
                new_iter = self._store.append(kind_iter, (pixbuf, 
                                                          tag.name, 
                                                          tag.kind.name, 
                                                          uri, 
                                                          tag.fields['line'], 
                                                          markup))
        # second level tags 
        for tag in tags:
            if "class" in tag.fields and "." not in tag.fields['class']:
                pixbuf = self.get_pixbuf(tag.kind.icon_name())
                if 'line' in tag.fields and self.show_line_numbers:
                    markup = "%s [%s]" % (tag.name, tag.fields['line'])
                else:
                    markup = tag.name
                for parent_tag in tags:
                    if parent_tag.name == tag.fields['class']:
                        break
                kind_iter = self._get_kind_iter(parent_tag.kind, uri, None)
                parent_iter = self._get_tag_iter(parent_tag, kind_iter)
                kind_iter = self._get_kind_iter(tag.kind, uri, parent_iter) # for sub-kind nodes
                new_iter = self._store.append(kind_iter, (pixbuf, 
                                                          tag.name, 
                                                          tag.kind.name, 
                                                          uri, 
                                                          tag.fields['line'], 
                                                          markup))
        # TODO: We need to go at least one more level to deal with the inline 
        # classes used in many python projects (eg. Models in Django)
        # Recursion would be even better.
        
        # sort                                        
        self._store.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        
        # expand
        if uri in self.expanded_rows:
            for strpath in self.expanded_rows[uri]:
                path = Gtk.TreePath.new_from_string(strpath)
                if path:
                    self._treeview.expand_row(path, False)
        elif uri not in self.expanded_rows and self.expand_rows:
            self._treeview.expand_all()
            """
            curiter = self._store.get_iter_first()
            while curiter:
                path = self._store.get_path(curiter)
                self._treeview.expand_row(path, False)
                curiter = self._store.iter_next(iter)
            """

    def on_row_activated(self, treeview, path, column, data=None):
        """
        If the row has uri and line number information, emits the tag-activated
        signal so that the editor can jump to the tag's location.
        """
        model = treeview.get_model()
        iter = model.get_iter(path)
        uri = model.get_value(iter, 3)
        line = model.get_value(iter, 4)
        if uri and line:
            self.emit("tag-activated", (uri, line))
    
    def on_row_collapsed(self, treeview, iter, path, data=None):
        """
        Remove the Gtk.TreePath of the expanded row from dict, so that the
        expanded rows will not be restored when switching between tabs.
        """      
        uri = self._store.get_value(iter, 3)
        path = str(path)
        if uri is not None:
            if uri in self.expanded_rows and path in self.expanded_rows[uri]:
                self.expanded_rows[uri].remove(path)
                #self._log.debug("Removing expanded row at %s", path)

    def on_row_expanded(self, treeview, iter, path, data=None):
        """
        Save the Gtk.TreePath of the expanded row, as a string, so that the
        expanded rows can be restored when switching between tabs.
        """
        uri = self._store.get_value(iter, 3)
        path = str(path)
        if uri is not None:
            if uri not in self.expanded_rows:
                self.expanded_rows[uri] = []
            if path not in self.expanded_rows[uri]:
                self.expanded_rows[uri].append(path)
                #self._log.debug("Adding expanded row at %s", path)
         
    def parse_file(self, path, uri):
        """
        Parse symbols out of a file using exhuberant ctags. The path is the local
        filename to pass to ctags, and the uri is the actual URI as known by
        Gedit. They would be different for remote files.
        """
        command = "ctags -n --fields=fiKlmnsSzt -f - %s" % path
        #self._log.debug(command)
        try:
            parser = ctags.Parser()
            parser.parse(command, self.ctags_executable)
        except Exception as e:
            self._log.warn("Could not execute ctags: %s (executable=%s)",
                           str(e), 
                           self.ctags_executable)
        self.load(parser.kinds, parser.tags, uri)
        
class SourceCodeBrowserPlugin(GObject.Object, Gedit.WindowActivatable):
    """
    Source Code Browser Plugin for Gedit 3.x
    
    Adds a tree view to the side panel of a Gedit window which provides a list
    of programming symbols (functions, classes, variables, etc.).
    
    https://live.gnome.org/Gedit/PythonPluginHowTo
    """
    __gtype_name__ = "SourceCodeBrowserPlugin"
    window = GObject.property(type=Gedit.Window)
    
    def __init__(self):
        GObject.Object.__init__(self)
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.setLevel(LOG_LEVEL)
        self._ctags_version = None
        
        # preferences
        # TODO: Put preferences into the config dialog
        self.load_remote_files = True
        self.ctags_executable = 'ctags'
        self.show_line_numbers = False
        self.expand_rows = True
        
        filename = os.path.join(ICON_DIR, "source-code-browser.png")
        self.icon = Gtk.Image.new_from_file(filename)

    def do_activate(self):
        """ Activate plugin """
        self._log.debug("Activating plugin")
        self._version_check()
        self._sourcetree = SourceTree()
        self._sourcetree.ctags_executable = self.ctags_executable
        self._sourcetree.show_line_numbers = self.show_line_numbers
        self._sourcetree.expand_rows = self.expand_rows
        panel = self.window.get_side_panel()
        panel.add_item(self._sourcetree, "SymbolBrowserPlugin", "Source Code", self.icon)
        
        if self.ctags_version is not None:
            self._sourcetree.connect('tag-activated', self.on_tag_activated)
            self.window.connect("active-tab-state-changed", self.on_tab_state_changed)
            self.window.connect("active-tab-changed", self.on_active_tab_changed)
            self.window.connect("tab-removed", self.on_tab_removed)
        else:
            self._sourcetree.set_sensitive(False)
    
    def do_deactivate(self):
        """ Deactivate the plugin """
        self._log.debug("Deactivating plugin")
        pane = self.window.get_side_panel()
        pane.remove_item(self._sourcetree)
    
    def do_update_state(self):
        pass
        
    def _load_active_document_symbols(self):
        """ Load the symbols for the given URI. """
        self._sourcetree.clear()
        #while Gtk.events_pending(): # <-- segfault
            #Gtk.main_iteration()
        document = self.window.get_active_document()
        if document:
            location = document.get_location()
            if location:
                uri = location.get_uri()
                self._log.debug("Loading %s...", uri)
                if uri is not None:
                    if uri[:7] == "file://":
                        filename = uri[7:]
                        self._sourcetree.parse_file(filename, uri)
                    elif self.load_remote_files:
                        basename = location.get_basename()
                        fd, filename = tempfile.mkstemp('.'+basename)
                        contents = document.get_text(document.get_start_iter(),
                                                     document.get_end_iter(),
                                                     True)
                        os.write(fd, contents)
                        os.close(fd)
                        while Gtk.events_pending():
                            Gtk.main_iteration()
                        self._sourcetree.parse_file(filename, uri)
                        os.unlink(filename)
                    self._loaded_document = document
                        
            
    def on_active_tab_changed(self, window, tab, data=None):
        self._log.debug("active-tab-changed")
        self._load_active_document_symbols()
    
    def on_tab_state_changed(self, window, data=None):
        self._log.debug("tab-state-changed")
        self._load_active_document_symbols()
    
    def on_tab_removed(self, window, tab, data=None):
        if not self.window.get_active_document():
            self._sourcetree.clear()
        
    def on_tag_activated(self, sourcetree, location, data=None):
        """ Go to the line where the double-clicked symbol is defined. """
        uri, line = location
        self._log.debug("%s, line %s." % (uri, line))
        document = self.window.get_active_document()
        view = self.window.get_active_view()
        line = int(line) - 1 # lines start from 0
        document.goto_line(line)
        view.scroll_to_cursor()
        
    def _version_check(self):
        """ Make sure the exhuberant ctags is installed. """
        self.ctags_version = ctags.get_ctags_version(self.ctags_executable) 
        if not self.ctags_version:
            self._log.warn("Could not find ctags executable: %s" % 
                           (self.ctags_executable))
            
        
        
