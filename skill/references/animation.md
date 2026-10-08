# PowerPoint OpenXML Animation Guide

## Purposeful Motion

Animations in LessonMorph exist solely to aid comprehension:
- Revealing sequential steps in a mathematical derivation or scientific process.
- Crossing out a common error before displaying the correct reasoning.
- Revealing the answer to a question only after students have had time to think.

## OpenXML Timing Injection

Rather than relying on proprietary tools or third-party desktop macros, LessonMorph directly modifies the presentation OpenXML package by injecting `<p:timing>` elements into `slide._element`:

```xml
<p:timing xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:tnLst>
    <p:par>
      <p:cTn id="1" dur="indefinite" restart="never" nodeType="tmRoot">
        <p:childTnLst>
          <p:seq concurrent="1" nextAc="seek">
            <p:cTn id="2" dur="indefinite" nodeType="mainSeq">
              <p:childTnLst>
                <!-- Animation step triggered on click -->
                <p:par>
                  <p:cTn id="3" fill="hold">
                    <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                    <p:childTnLst>
                      <p:par>
                        <p:cTn id="4" fill="hold">
                          <p:stCondLst><p:cond delay="0"/></p:stCondLst>
                          <p:childTnLst>
                            <p:animEffect transition="in" filter="fade">
                              <p:cBhvr>
                                <p:cTn id="5" dur="500"/>
                                <p:tgtEl><p:spTgt spid="{shape_id}"/></p:tgtEl>
                              </p:cBhvr>
                            </p:animEffect>
                          </p:childTnLst>
                        </p:cTn>
                      </p:par>
                    </p:childTnLst>
                  </p:cTn>
                </p:par>
              </p:childTnLst>
            </p:cTn>
          </p:seq>
        </p:childTnLst>
      </p:cTn>
    </p:par>
  </p:tnLst>
  <p:bldLst>
    <p:bldP spid="{shape_id}" grpId="0" build="asOne"/>
  </p:bldLst>
</p:timing>
```

This guarantees that animations play natively when opened in Microsoft PowerPoint on Windows, macOS, or PowerPoint for the Web, without requiring third-party plugins.
