# GTK Builder translation rules

`its/gtkbuilder.its` and `its/gtkbuilder.loc` are copied without modification from
GTK tag `3.24.51`, under GTK's LGPL license (see COPYING).

Sources:
- https://github.com/GNOME/gtk/blob/3.24.51/gtk/gtkbuilder.its
- https://github.com/GNOME/gtk/blob/3.24.51/gtk/gtkbuilder.loc

SHA256:
- gtkbuilder.its: `2f046ff55a37e60e2d243614ddf6c6c3d4df91fa4471ce69cdcaa0ca3c147710`
- gtkbuilder.loc: `0ab0098e29c47560a578361cbe8290a02d04b17f0609069c809efb005f7e2d74`

Orca uses these upstream rules explicitly through GETTEXTDATADIRS instead of
gettext's fallback rules. Only the build environment uses them; they do not add
GTK development packages to the ISO.
