

PROMPT = """Please determine whether the human motion in the video is aligned with the text within the <Instruction> tags. 

<Instruction>
{input_text}
</Instruction>

You need to make this judgment based on naturalness and faithfulness. 
Please directly answer "Yes" for aligned motion and "No" for unaligned motion:"""