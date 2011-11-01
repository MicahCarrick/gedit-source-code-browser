from gi.repository import GObject, Gtk, GtkSource, Gedit

class Proposal(GObject.Object, GtkSource.CompletionProposal):
        __gtype_name__ = "GeditSourceCodeProposal"
        

        def __init__(self, tag):
                GObject.Object.__init__(self)
                self._tag = tag

        # Interface implementation
        def do_get_markup(self):
                return self._tag.name

        """
        def do_get_info(self):
                return self._tag.name
        """

class Provider(GObject.Object, GtkSource.CompletionProvider):
        __gtype_name__ = "GeditSourceCodeProvider"

        def __init__(self, sourcetree):
                GObject.Object.__init__(self)
                self.name = 'SourceCodeProvider'
                self.sourcetree = sourcetree
                """
                theme = Gtk.IconTheme.get_default()
                f, w, h = Gtk.icon_size_lookup(Gtk.IconSize.MENU)

                try:
                        self.icon = theme.load_icon(Gtk.STOCK_JUSTIFY_LEFT, w, 0)
                except:
                        self.icon = None
                """
                self.icon = self.sourcetree.get_pixbuf('source-code-browser')

        def get_word(self, context):
                it = context.get_iter()

                if it.starts_word() or it.starts_line() or not it.ends_word():
                        return None

                start = it.copy()

                if start.backward_word_start():
                        return start.get_text(it)
                else:
                        return None

        def do_match(self, context):
                return True

        def do_populate(self, context):
                word = self.get_word(context)
                proposals = []
                print word
                for tag in self.sourcetree.tags:
                        if not word or tag.name.startswith(word):
                                proposals.append(Proposal(tag))
                context.add_proposals(self, proposals, True)

        def do_get_name(self):
                return self.name

        def do_activate_proposal(self, proposal, piter):
                buf = piter.get_buffer()
                buf.insert_at_cursor(proposal._tag.name, -1)
                return True

        def do_get_icon(self):
                return self.icon

        def do_get_activation(self):
                return GtkSource.CompletionActivation.USER_REQUESTED

# ex:ts=8:et:
