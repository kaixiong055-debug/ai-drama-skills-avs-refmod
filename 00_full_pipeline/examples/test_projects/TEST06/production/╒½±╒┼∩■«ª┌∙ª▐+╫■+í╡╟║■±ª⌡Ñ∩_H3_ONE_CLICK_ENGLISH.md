[Spatial Warm-up LOCK_SC01_A01 | 1s | Hidden spatial warm-up]
[Scene] SCN_LIVING_NIGHT | the living room at night
[Episode] EP01 | Chapter 1
[H3 Mode] REF2VA
[Include In Final] NO
[Continuity] INDEPENDENT

subject_definitions:
<Subject 1> is Gu Yanchuan (CHAR_A); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 2> is Lin Wanqing (CHAR_B); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 3> is Chen Yue (CHAR_C); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 4>: the living room at night; All scene references describe one environment subject.

summary:
A natural cinematic drama with consistent characters and stable indoor lighting
Establish a spatial anchor without executing the formal story.
spatial_state:
spatial_measurement: RELATIVE; confidence=UNKNOWN
area=main area; scene_variant=master location; present_count=3
Gu Yanchuan (CHAR_A): screen_position=screen left; depth=foreground; facing=screen right; eyeline=Lin Wanqing.
Lin Wanqing (CHAR_B): screen_position=central position 2 of 3; depth=foreground; facing=screen left; eyeline=Gu Yanchuan.
Chen Yue (CHAR_C): screen_position=screen right; depth=midground; facing=screen left; eyeline=Gu Yanchuan.
Gu Yanchuan, Lin Wanqing: Adjacent, maintaining the established relative spacing; metric scale is unspecified
Gu Yanchuan, Chen Yue: Maintain the established lateral and depth relationship; metric scale is unspecified
Lin Wanqing, Chen Yue: Maintain the established lateral and depth relationship; metric scale is unspecified
geometry.fixed_architecture.walls=rectangular living room; fixed north wall
geometry.door_positions.ENTRY_DOOR=rear left
geometry.window_positions.WINDOW=rear right
geometry.furniture_positions.SOFA=behind the characters on the right
geometry.furniture_positions.TABLE=foreground center
geometry.furniture_positions.CHAIR=midground left
geometry.entrance_positions.ENTRY_DOOR=enter from rear left
geometry.exit_positions.ENTRY_DOOR=exit toward rear left
dialogue_group=Gu Yanchuan, Lin Wanqing

continuity_state:
incoming_state: Initialize the declared scene independently.
current_state:
valid_until_changed=true; The declared baseline persists to the end unless an explicit event changes it.
No props are currently held or registered.
door_states: ENTRY_DOOR=closed
completed_actions: none
completed_sounds: none
end_state: Hold the baseline and finish in a stable pose; complete no story action or sound event.
from_previous: No dynamic input.
to_next: SEG001

camera_plan:
camera_side=south; dialogue_axis=locked east-west axis
When cutting from a group shot to a character close-up, only the camera framing, focal length, and composition change. The character's physical position in the scene does not change. Off-screen characters remain in their previously established spatial positions.
Stable wide shot; locked-off camera; show all present characters and key fixed structures.

shot_timeline:
[Shot 1 | 0.000–1.000s]
Only natural breathing and tiny head movements; no walking, crossing, swaps or complex actions; finish on a clean stable frame.

dialogue_and_audio:
No dialogue or key sound events.
Ambience: quiet indoor room tone and subtle breathing
non_diegetic_music=N/A

reference_map:
P1=CHAR_A_H3_OFFICE.png; <Picture 1> → <Subject 1>; asset_id=CHAR_A_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P2=CHAR_B_H3_OFFICE.png; <Picture 2> → <Subject 2>; asset_id=CHAR_B_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P3=CHAR_C_H3_OFFICE.png; <Picture 3> → <Subject 3>; asset_id=CHAR_C_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P4=SCN_LIVING_MASTER.png; <Picture 4> → <Subject 4>; asset_id=SCN_LIVING_MASTER; Controls fixed architecture, doors, windows, furniture and real scene geometry; does not lock the source camera; story lighting, time and weather take precedence.
Hidden LOCK: LOCK_SC01_A01; Provides the spatial anchor and is excluded from the formal 5s and final assembly.
continuation_source=NONE; Supply the last 22 frames to AddGuide for the following formal segment.

negative_rules:
Do not change faces, apparent age, identity, or body proportions.
Do not change wardrobe, hairstyle, or wet/dry hair states without a scripted cause.
Do not randomly swap left/right positions, teleport characters in close-ups, or rearrange off-screen characters.
Do not cross the dialogue axis without authorization, mirror the image, or reverse left/right roads.
Do not move doors or windows, add doors, remove fixed furniture, or redesign the location.
Do not spawn or remove props, switch holding hands, or change holders without a scripted transfer.
No extra hands or arms, fused limbs, or deformed hands; each person has exactly two hands.
Do not repeat completed actions or retrigger completed sound events.
No random deformation during the final second, excessive motion blur, added text, or watermarks; scripted readable text must match the bound asset exactly.
Do not automatically add background music.

[Video Segment 1 | 5s | Night | A short exchange between roommates]
[Scene] SCN_LIVING_NIGHT | the living room at night
[Episode] EP01 | Chapter 1
[H3 Mode] REF2VA
[Include In Final] YES
[Continuity] CONTINUATION

subject_definitions:
<Subject 1> is Gu Yanchuan (CHAR_A); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 2> is Lin Wanqing (CHAR_B); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 3> is Chen Yue (CHAR_C); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 4>: the living room at night; All scene references describe one environment subject.

summary:
A natural cinematic drama with consistent characters and stable indoor lighting
The characters exchange a question and answer from their fixed living-room positions
spatial_state:
spatial_measurement: RELATIVE; confidence=UNKNOWN
area=main area; scene_variant=master location; present_count=3
Gu Yanchuan (CHAR_A): screen_position=screen left; depth=foreground; facing=screen right; eyeline=Lin Wanqing.
Lin Wanqing (CHAR_B): screen_position=central position 2 of 3; depth=foreground; facing=screen left; eyeline=Gu Yanchuan.
Chen Yue (CHAR_C): screen_position=screen right; depth=midground; facing=screen left; eyeline=Gu Yanchuan.
Gu Yanchuan, Lin Wanqing: Adjacent, maintaining the established relative spacing; metric scale is unspecified
Gu Yanchuan, Chen Yue: Maintain the established lateral and depth relationship; metric scale is unspecified
Lin Wanqing, Chen Yue: Maintain the established lateral and depth relationship; metric scale is unspecified
geometry.fixed_architecture.walls=rectangular living room; fixed north wall
geometry.door_positions.ENTRY_DOOR=rear left
geometry.window_positions.WINDOW=rear right
geometry.furniture_positions.SOFA=behind the characters on the right
geometry.furniture_positions.TABLE=foreground center
geometry.furniture_positions.CHAIR=midground left
geometry.entrance_positions.ENTRY_DOOR=enter from rear left
geometry.exit_positions.ENTRY_DOOR=exit toward rear left
dialogue_group=Gu Yanchuan, Lin Wanqing
primary_listener=Chen Yue; secondary_listeners=none

continuity_state:
incoming_state: SEG001_INCOMING
The entry state equals this segment’s declared baseline; no additional state transition is pending.
current_state: SEG001_CURRENT
valid_until_changed=true; The declared baseline persists to the end unless an explicit event changes it.
No props are currently held or registered.
door_states: ENTRY_DOOR=closed
completed_actions: none
completed_sounds: none
end_state: SEG001_END
At 5s there is no state change; every field of the current baseline remains valid.
from_previous: Continue visual motion only; do not inherit completed audio tails.
to_next: SEG002 receives this segment’s end state; rebuild a LOCK if the spatial anchor is invalidated.

camera_plan:
camera_side=south; dialogue_axis=locked east-west axis
When cutting from a group shot to a character close-up, only the camera framing, focal length, and composition change. The character's physical position in the scene does not change. Off-screen characters remain in their previously established spatial positions.
Settings shared by all shots: shot_scale=close-up; lens=85mm; planned camera height=1.5m; camera_movement=locked-off camera; camera_angle=a three-quarter reverse angle on the same side of the dialogue axis; composition=Frame the current speaker’s face and shoulders; all others remain off-screen in their established positions; lighting=soft window-side key light and consistent indoor fill; depth_of_field=shallow depth of field with a clearly readable face
Shot 1 (SH001): Apply the shared shot settings declared in this segment. Cut purpose: show the current speaker’s subtle reaction
Shot 2 (SH002): Apply the shared shot settings declared in this segment. Cut purpose: show the current speaker’s subtle reaction

shot_timeline:
[Shot 1 | 0.000–2.500s]
SH001: The speaker breathes subtly and keeps the eyeline toward the listener
Perform beats: B001 (Gu Yanchuan)
B001: Remain in the established position and deliver the short line
[Shot 2 | 2.500–5.000s]
SH002: The speaker breathes subtly and keeps the eyeline toward the listener
Perform beats: B002 (Lin Wanqing)
B002: Remain in the established position and deliver the short line
Use natural, restrained expressions and subtle movements. Off-screen characters do not move.

dialogue_and_audio:
B001 | 0.200–2.200s | Gu Yanchuan | restrained and natural: <d>[Chinese] 你笑了？</d>
B002 | 2.700–4.500s | Lin Wanqing | restrained and natural: <d>[Chinese] 没有。</d>
Ambience: quiet indoor room tone and subtle breathing
non_diegetic_music=N/A

reference_map:
P1=CHAR_A_H3_OFFICE.png; <Picture 1> → <Subject 1>; asset_id=CHAR_A_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P2=CHAR_B_H3_OFFICE.png; <Picture 2> → <Subject 2>; asset_id=CHAR_B_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P3=CHAR_C_H3_OFFICE.png; <Picture 3> → <Subject 3>; asset_id=CHAR_C_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P4=SCN_LIVING_MASTER.png; <Picture 4> → <Subject 4>; asset_id=SCN_LIVING_MASTER; Controls fixed architecture, doors, windows, furniture and real scene geometry; does not lock the source camera; story lighting, time and weather take precedence.
Hidden LOCK: LOCK_SC01_A01; Provides the spatial anchor and is excluded from the formal 5s and final assembly.
continuation_source=LOCK_SC01_A01; tail_frames=22; fps=24; AddGuide.frame_idx=0; inherit_audio=false; Deliver a full 5s of formal content; generate 142 frames and trim only the 22-frame overlap.

negative_rules:
Do not change faces, apparent age, identity, or body proportions.
Do not change wardrobe, hairstyle, or wet/dry hair states without a scripted cause.
Do not randomly swap left/right positions, teleport characters in close-ups, or rearrange off-screen characters.
Do not cross the dialogue axis without authorization, mirror the image, or reverse left/right roads.
Do not move doors or windows, add doors, remove fixed furniture, or redesign the location.
Do not spawn or remove props, switch holding hands, or change holders without a scripted transfer.
No extra hands or arms, fused limbs, or deformed hands; each person has exactly two hands.
Do not repeat completed actions or retrigger completed sound events.
No random deformation during the final second, excessive motion blur, added text, or watermarks; scripted readable text must match the bound asset exactly.
Do not automatically add background music.

[Spatial Warm-up LOCK_SC01_A02 | 1s | Hidden spatial warm-up]
[Scene] SCN_LIVING_NIGHT | the living room at night
[Episode] EP01 | Chapter 1
[H3 Mode] REF2VA
[Include In Final] NO
[Continuity] INDEPENDENT

subject_definitions:
<Subject 1> is Gu Yanchuan (CHAR_A); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 2> is Lin Wanqing (CHAR_B); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 3>: the living room at night; All scene references describe one environment subject.

summary:
A natural cinematic drama with consistent characters and stable indoor lighting
Establish a spatial anchor without executing the formal story.
spatial_state:
spatial_measurement: RELATIVE; confidence=UNKNOWN
area=main area; scene_variant=master location; present_count=2
Gu Yanchuan (CHAR_A): screen_position=screen left; depth=foreground; facing=screen right; eyeline=Lin Wanqing.
Lin Wanqing (CHAR_B): screen_position=screen right; depth=foreground; facing=screen left; eyeline=Gu Yanchuan.
Gu Yanchuan, Lin Wanqing: Adjacent, maintaining the established relative spacing; metric scale is unspecified
geometry.fixed_architecture.walls=rectangular living room; fixed north wall
geometry.door_positions.ENTRY_DOOR=rear left
geometry.window_positions.WINDOW=rear right
geometry.furniture_positions.SOFA=behind the characters on the right
geometry.furniture_positions.TABLE=foreground center
geometry.furniture_positions.CHAIR=midground left
geometry.entrance_positions.ENTRY_DOOR=enter from rear left
geometry.exit_positions.ENTRY_DOOR=exit toward rear left
dialogue_group=Gu Yanchuan, Lin Wanqing

continuity_state:
incoming_state: Initialize the declared scene independently.
current_state:
valid_until_changed=true; The declared baseline persists to the end unless an explicit event changes it.
No props are currently held or registered.
door_states: ENTRY_DOOR=closed
completed_actions: none
completed_sounds: none
end_state: Hold the baseline and finish in a stable pose; complete no story action or sound event.
from_previous: No dynamic input.
to_next: SEG002

camera_plan:
camera_side=south; dialogue_axis=locked east-west axis
When cutting from a group shot to a character close-up, only the camera framing, focal length, and composition change. The character's physical position in the scene does not change. Off-screen characters remain in their previously established spatial positions.
Stable wide shot; locked-off camera; show all present characters and key fixed structures.

shot_timeline:
[Shot 1 | 0.000–1.000s]
Only natural breathing and tiny head movements; no walking, crossing, swaps or complex actions; finish on a clean stable frame.

dialogue_and_audio:
No dialogue or key sound events.
Ambience: quiet indoor room tone and subtle breathing
non_diegetic_music=N/A

reference_map:
P1=CHAR_A_H3_OFFICE.png; <Picture 1> → <Subject 1>; asset_id=CHAR_A_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P2=CHAR_B_H3_OFFICE.png; <Picture 2> → <Subject 2>; asset_id=CHAR_B_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P3=SCN_LIVING_MASTER.png; <Picture 3> → <Subject 3>; asset_id=SCN_LIVING_MASTER; Controls fixed architecture, doors, windows, furniture and real scene geometry; does not lock the source camera; story lighting, time and weather take precedence.
Hidden LOCK: LOCK_SC01_A02; Provides the spatial anchor and is excluded from the formal 5s and final assembly.
continuation_source=NONE; Supply the last 22 frames to AddGuide for the following formal segment.

negative_rules:
Do not change faces, apparent age, identity, or body proportions.
Do not change wardrobe, hairstyle, or wet/dry hair states without a scripted cause.
Do not randomly swap left/right positions, teleport characters in close-ups, or rearrange off-screen characters.
Do not cross the dialogue axis without authorization, mirror the image, or reverse left/right roads.
Do not move doors or windows, add doors, remove fixed furniture, or redesign the location.
Do not spawn or remove props, switch holding hands, or change holders without a scripted transfer.
No extra hands or arms, fused limbs, or deformed hands; each person has exactly two hands.
Do not repeat completed actions or retrigger completed sound events.
No random deformation during the final second, excessive motion blur, added text, or watermarks; scripted readable text must match the bound asset exactly.
Do not automatically add background music.

[Video Segment 2 | 5s | Night | A short exchange between roommates]
[Scene] SCN_LIVING_NIGHT | the living room at night
[Episode] EP01 | Chapter 1
[H3 Mode] REF2VA
[Include In Final] YES
[Continuity] CONTINUATION

subject_definitions:
<Subject 1> is Gu Yanchuan (CHAR_A); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 2> is Lin Wanqing (CHAR_B); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 3>: the living room at night; All scene references describe one environment subject.

summary:
A natural cinematic drama with consistent characters and stable indoor lighting
The characters exchange a question and answer from their fixed living-room positions
spatial_state:
spatial_measurement: RELATIVE; confidence=UNKNOWN
area=main area; scene_variant=master location; present_count=2
Gu Yanchuan (CHAR_A): screen_position=screen left; depth=foreground; facing=screen right; eyeline=Lin Wanqing.
Lin Wanqing (CHAR_B): screen_position=screen right; depth=foreground; facing=screen left; eyeline=Gu Yanchuan.
Gu Yanchuan, Lin Wanqing: Adjacent, maintaining the established relative spacing; metric scale is unspecified
geometry.fixed_architecture.walls=rectangular living room; fixed north wall
geometry.door_positions.ENTRY_DOOR=rear left
geometry.window_positions.WINDOW=rear right
geometry.furniture_positions.SOFA=behind the characters on the right
geometry.furniture_positions.TABLE=foreground center
geometry.furniture_positions.CHAIR=midground left
geometry.entrance_positions.ENTRY_DOOR=enter from rear left
geometry.exit_positions.ENTRY_DOOR=exit toward rear left
dialogue_group=Gu Yanchuan, Lin Wanqing
primary_listener=none; secondary_listeners=none

continuity_state:
incoming_state: SEG002_INCOMING
Lin Wanqing (CHAR_B): screen_position=central position 2 of 3; depth=foreground; facing=screen left; eyeline=Gu Yanchuan.
Chen Yue is now present.
Chen Yue: wardrobe=a black office suit
Chen Yue: hair_state=dry
Chen Yue: clothing_state=dry and intact
Chen Yue: pose=standing naturally
Chen Yue (CHAR_C): screen_position=screen right; depth=midground; facing=screen left; eyeline=Gu Yanchuan.
current_state: SEG002_CURRENT
valid_until_changed=true; The declared baseline persists to the end unless an explicit event changes it.
No props are currently held or registered.
door_states: ENTRY_DOOR=closed
completed_actions: none
completed_sounds: none
end_state: SEG002_END
At 5s there is no state change; every field of the current baseline remains valid.
from_previous: Continue visual motion only; do not inherit completed audio tails.
to_next: SEG003 receives this segment’s end state; rebuild a LOCK if the spatial anchor is invalidated.
Completed before this segment: Chen Yue leaves through the fixed doorway

camera_plan:
camera_side=south; dialogue_axis=locked east-west axis
When cutting from a group shot to a character close-up, only the camera framing, focal length, and composition change. The character's physical position in the scene does not change. Off-screen characters remain in their previously established spatial positions.
Settings shared by all shots: shot_scale=close-up; lens=85mm; planned camera height=1.5m; camera_movement=locked-off camera; camera_angle=a three-quarter reverse angle on the same side of the dialogue axis; composition=Frame the current speaker’s face and shoulders; all others remain off-screen in their established positions; lighting=soft window-side key light and consistent indoor fill; depth_of_field=shallow depth of field with a clearly readable face
Shot 1 (SH003): Apply the shared shot settings declared in this segment. Cut purpose: show the current speaker’s subtle reaction
Shot 2 (SH004): Apply the shared shot settings declared in this segment. Cut purpose: show the current speaker’s subtle reaction

shot_timeline:
[Shot 1 | 0.000–2.500s]
SH003: The speaker breathes subtly and keeps the eyeline toward the listener
Perform beats: B003 (Gu Yanchuan)
B003: Remain in the established position and deliver the short line
[Shot 2 | 2.500–5.000s]
SH004: The speaker breathes subtly and keeps the eyeline toward the listener
Perform beats: B004 (Lin Wanqing)
B004: Remain in the established position and deliver the short line
Use natural, restrained expressions and subtle movements. Off-screen characters do not move.

dialogue_and_audio:
B003 | 0.200–2.200s | Gu Yanchuan | restrained and natural: <d>[Chinese] 你笑了？</d>
B004 | 2.700–4.500s | Lin Wanqing | restrained and natural: <d>[Chinese] 没有。</d>
Ambience: quiet indoor room tone and subtle breathing
non_diegetic_music=N/A

reference_map:
P1=CHAR_A_H3_OFFICE.png; <Picture 1> → <Subject 1>; asset_id=CHAR_A_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P2=CHAR_B_H3_OFFICE.png; <Picture 2> → <Subject 2>; asset_id=CHAR_B_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P3=SCN_LIVING_MASTER.png; <Picture 3> → <Subject 3>; asset_id=SCN_LIVING_MASTER; Controls fixed architecture, doors, windows, furniture and real scene geometry; does not lock the source camera; story lighting, time and weather take precedence.
Hidden LOCK: LOCK_SC01_A02; Provides the spatial anchor and is excluded from the formal 5s and final assembly.
continuation_source=LOCK_SC01_A02; tail_frames=22; fps=24; AddGuide.frame_idx=0; inherit_audio=false; Deliver a full 5s of formal content; generate 142 frames and trim only the 22-frame overlap.

negative_rules:
Do not change faces, apparent age, identity, or body proportions.
Do not change wardrobe, hairstyle, or wet/dry hair states without a scripted cause.
Do not randomly swap left/right positions, teleport characters in close-ups, or rearrange off-screen characters.
Do not cross the dialogue axis without authorization, mirror the image, or reverse left/right roads.
Do not move doors or windows, add doors, remove fixed furniture, or redesign the location.
Do not spawn or remove props, switch holding hands, or change holders without a scripted transfer.
No extra hands or arms, fused limbs, or deformed hands; each person has exactly two hands.
Do not repeat completed actions or retrigger completed sound events.
No random deformation during the final second, excessive motion blur, added text, or watermarks; scripted readable text must match the bound asset exactly.
Do not automatically add background music.

[Video Segment 3 | 5s | Night | A short exchange between roommates]
[Scene] SCN_LIVING_NIGHT | the living room at night
[Episode] EP01 | Chapter 1
[H3 Mode] REF2VA
[Include In Final] YES
[Continuity] CONTINUATION

subject_definitions:
<Subject 1> is Gu Yanchuan (CHAR_A); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 2> is Lin Wanqing (CHAR_B); an adult approximately 28 years old with consistent facial features and body proportions; hairstyle=neatly styled black hair; wardrobe=a black office suit; hair_state=dry; clothing_state=dry and intact; pose=standing naturally.
<Subject 3>: the living room at night; All scene references describe one environment subject.

summary:
A natural cinematic drama with consistent characters and stable indoor lighting
The characters exchange a question and answer from their fixed living-room positions
spatial_state:
spatial_measurement: RELATIVE; confidence=UNKNOWN
area=main area; scene_variant=master location; present_count=2
Gu Yanchuan (CHAR_A): screen_position=screen left; depth=foreground; facing=screen right; eyeline=Lin Wanqing.
Lin Wanqing (CHAR_B): screen_position=screen right; depth=foreground; facing=screen left; eyeline=Gu Yanchuan.
Gu Yanchuan, Lin Wanqing: Adjacent, maintaining the established relative spacing; metric scale is unspecified
geometry.fixed_architecture.walls=rectangular living room; fixed north wall
geometry.door_positions.ENTRY_DOOR=rear left
geometry.window_positions.WINDOW=rear right
geometry.furniture_positions.SOFA=behind the characters on the right
geometry.furniture_positions.TABLE=foreground center
geometry.furniture_positions.CHAIR=midground left
geometry.entrance_positions.ENTRY_DOOR=enter from rear left
geometry.exit_positions.ENTRY_DOOR=exit toward rear left
dialogue_group=Gu Yanchuan, Lin Wanqing
primary_listener=none; secondary_listeners=none

continuity_state:
incoming_state: SEG003_INCOMING
The entry state equals this segment’s declared baseline; no additional state transition is pending.
current_state: SEG003_CURRENT
valid_until_changed=true; The declared baseline persists to the end unless an explicit event changes it.
No props are currently held or registered.
door_states: ENTRY_DOOR=closed
completed_actions: none
completed_sounds: none
end_state: SEG003_END
At 5s there is no state change; every field of the current baseline remains valid.
from_previous: Continue visual motion only; do not inherit completed audio tails.
to_next: This segment closes the project.

camera_plan:
camera_side=south; dialogue_axis=locked east-west axis
When cutting from a group shot to a character close-up, only the camera framing, focal length, and composition change. The character's physical position in the scene does not change. Off-screen characters remain in their previously established spatial positions.
Settings shared by all shots: shot_scale=close-up; lens=85mm; planned camera height=1.5m; camera_movement=locked-off camera; camera_angle=a three-quarter reverse angle on the same side of the dialogue axis; composition=Frame the current speaker’s face and shoulders; all others remain off-screen in their established positions; lighting=soft window-side key light and consistent indoor fill; depth_of_field=shallow depth of field with a clearly readable face
Shot 1 (SH005): Apply the shared shot settings declared in this segment. Cut purpose: show the current speaker’s subtle reaction
Shot 2 (SH006): Apply the shared shot settings declared in this segment. Cut purpose: show the current speaker’s subtle reaction

shot_timeline:
[Shot 1 | 0.000–2.500s]
SH005: The speaker breathes subtly and keeps the eyeline toward the listener
Perform beats: B005 (Gu Yanchuan)
B005: Remain in the established position and deliver the short line
[Shot 2 | 2.500–5.000s]
SH006: The speaker breathes subtly and keeps the eyeline toward the listener
Perform beats: B006 (Lin Wanqing)
B006: Remain in the established position and deliver the short line
Use natural, restrained expressions and subtle movements. Off-screen characters do not move.

dialogue_and_audio:
B005 | 0.200–2.200s | Gu Yanchuan | restrained and natural: <d>[Chinese] 你笑了？</d>
B006 | 2.700–4.500s | Lin Wanqing | restrained and natural: <d>[Chinese] 没有。</d>
Ambience: quiet indoor room tone and subtle breathing
non_diegetic_music=N/A

reference_map:
P1=CHAR_A_H3_OFFICE.png; <Picture 1> → <Subject 1>; asset_id=CHAR_A_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P2=CHAR_B_H3_OFFICE.png; <Picture 2> → <Subject 2>; asset_id=CHAR_B_H3_OFFICE; Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera. wardrobe=OFFICE
P3=SCN_LIVING_MASTER.png; <Picture 3> → <Subject 3>; asset_id=SCN_LIVING_MASTER; Controls fixed architecture, doors, windows, furniture and real scene geometry; does not lock the source camera; story lighting, time and weather take precedence.
Hidden LOCK: LOCK_SC01_A02; Provides the spatial anchor and is excluded from the formal 5s and final assembly.
continuation_source=SEG002; tail_frames=22; fps=24; AddGuide.frame_idx=0; inherit_audio=false; Deliver a full 5s of formal content; generate 142 frames and trim only the 22-frame overlap.

negative_rules:
Do not change faces, apparent age, identity, or body proportions.
Do not change wardrobe, hairstyle, or wet/dry hair states without a scripted cause.
Do not randomly swap left/right positions, teleport characters in close-ups, or rearrange off-screen characters.
Do not cross the dialogue axis without authorization, mirror the image, or reverse left/right roads.
Do not move doors or windows, add doors, remove fixed furniture, or redesign the location.
Do not spawn or remove props, switch holding hands, or change holders without a scripted transfer.
No extra hands or arms, fused limbs, or deformed hands; each person has exactly two hands.
Do not repeat completed actions or retrigger completed sound events.
No random deformation during the final second, excessive motion blur, added text, or watermarks; scripted readable text must match the bound asset exactly.
Do not automatically add background music.

