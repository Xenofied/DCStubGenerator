# DC Files
# This is, oddly enough, in *reverse* order of their loading...
dc-file toon.dc
dc-file otp.dc


# Ignore certain class delimiters
ignore-client #f
ignore-AI #f
ignore-UD #f
ignore-OV #f

overwrite-files #f


# Enabling this generates a file for each dclass, even if they aren't imported.
generate-non-import-dclasses #f

# Enabling this makes the writer write  __init__ methods for classes.
generate-init #t
