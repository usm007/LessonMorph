"""OOXML Animation Engine for PowerPoint presentations.

Generates compliant OpenXML <p:timing> sequences to produce native PowerPoint
on-click animations (progressive stepped builds, misconception reveals, answer reveals).
"""

from __future__ import annotations
from typing import List, Tuple
from pptx.oxml import parse_xml
from pptx.oxml.ns import nsdecls
from lessonmorph.core.models import AnimationStep, AnimationType
from lessonmorph.animation.presets import PRESETS


class OoxmlAnimationEngine:
    """Injects native OpenXML animation sequences into python-pptx slide elements."""

    @classmethod
    def apply_animations(cls, slide, animation_steps: List[Tuple[int, AnimationType]]) -> None:
        """
        Takes a python-pptx slide and a list of (shape_id, AnimationType) tuples.
        Injects a valid <p:timing> element.
        """
        if not animation_steps:
            return

        # Generate unique IDs for XML nodes
        id_counter = 1

        def next_id():
            nonlocal id_counter
            id_counter += 1
            return str(id_counter)

        # Build individual animation action paragraphs
        child_pars_xml = []
        bld_p_xml = []

        for shape_id, anim_type in animation_steps:
            preset = PRESETS.get(anim_type, PRESETS[AnimationType.APPEAR])
            c_tn_1 = next_id()
            c_tn_2 = next_id()
            c_tn_3 = next_id()

            child_pars_xml.append(f"""
              <p:par>
                <p:cTn id="{c_tn_1}" fill="hold">
                  <p:stCondLst>
                    <p:cond delay="{preset.trigger_delay_ms}"/>
                  </p:stCondLst>
                  <p:childTnLst>
                    <p:par>
                      <p:cTn id="{c_tn_2}" fill="hold">
                        <p:stCondLst>
                          <p:cond delay="0"/>
                        </p:stCondLst>
                        <p:childTnLst>
                          <p:animEffect transition="{preset.transition_direction}" filter="{preset.filter_effect}">
                            <p:cBhvr>
                              <p:cTn id="{c_tn_3}" dur="{preset.duration_ms}"/>
                              <p:tgtEl>
                                <p:spTgt spid="{shape_id}"/>
                              </p:tgtEl>
                            </p:cBhvr>
                          </p:animEffect>
                        </p:childTnLst>
                      </p:cTn>
                    </p:par>
                  </p:childTnLst>
                </p:cTn>
              </p:par>
            """)

            bld_p_xml.append(f'<p:bldP spid="{shape_id}" grpId="0" build="asOne"/>')

        steps_joined = "\n".join(child_pars_xml)
        bld_joined = "\n".join(bld_p_xml)

        timing_xml = f"""
        <p:timing {nsdecls("p")}>
          <p:tnLst>
            <p:par>
              <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
                <p:childTnLst>
                  <p:seq concurrent="1" nextAc="seek">
                    <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
                      <p:childTnLst>
                        {steps_joined}
                      </p:childTnLst>
                    </p:cTn>
                    <p:prevCondLst>
                      <p:cond evt="onPrev" delay="0">
                        <p:tgtEl><p:sldTgt/></p:tgtEl>
                      </p:cond>
                    </p:prevCondLst>
                    <p:nextCondLst>
                      <p:cond evt="onNext" delay="0">
                        <p:tgtEl><p:sldTgt/></p:tgtEl>
                      </p:cond>
                    </p:nextCondLst>
                  </p:seq>
                </p:childTnLst>
              </p:cTn>
            </p:par>
          </p:tnLst>
          <p:bldLst>
            {bld_joined}
          </p:bldLst>
        </p:timing>
        """

        try:
            timing_elem = parse_xml(timing_xml)
            slide._element.append(timing_elem)
        except Exception as e:
            # Fallback gracefully if XML parsing has issue
            print(f"[LessonMorph Animation] Warning: could not apply timing XML: {e}")
