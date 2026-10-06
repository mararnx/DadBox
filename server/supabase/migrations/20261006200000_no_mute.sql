-- There is no mute (ADR 0020). The box has ignored it since then, and
-- PATCH /settings now refuses it; drop the stored flags and who set them.
update settings
   set value = value - 'mute',
       meta  = meta - 'mute.a' - 'mute.b'
 where id;
