#!/usr/bin/env rake

PLUGIN_DIR = File.join(ENV['HOME'], '.config', 'gedit', 'plugins')
SCHEMA_DIR = File.join('/', 'usr', 'share', 'glib-2.0', 'schemas')

desc "Install sourcecodebrowser to #{PLUGIN_DIR}. If we're run as root, also " +
     "install our schema to #{SCHEMA_DIR}."
task :install do
	mkdir_p PLUGIN_DIR
	cp_r 'sourcecodebrowser', PLUGIN_DIR
	cp 'sourcecodebrowser.plugin', PLUGIN_DIR

	if ENV['USER'] == 'root'
		cp_r(File.join(PLUGIN_DIR, 'sourcecodebrowser', 'data',
		               'org.gnome.gedit.plugins.sourcecodebrowser.gschema.xml'),
		     SCHEMA_DIR)
		system "glib-compile-schemas #{SCHEMA_DIR}"
	else
		warn "To enable our configuration dialog, rerun `rake install` as root."
	end
end
