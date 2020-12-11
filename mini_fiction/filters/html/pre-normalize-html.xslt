<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:re="http://exslt.org/regular-expressions"
    xmlns:str="http://exslt.org/strings"
    extension-element-prefixes="re str">
    
    <xsl:param name="convert_linebreaks" select="false()"/>
    <xsl:param name="br_to_p" select="false()"/>
    
<xsl:template match="*[@block-element]" priority="2">
    <p-splitter/>
    <xsl:copy>
        <xsl:apply-templates select="@*"/>
        <p root-paragraph="true"><xsl:apply-templates select="node()"/></p>
    </xsl:copy>
    <p-splitter/>
</xsl:template>
    
<xsl:template match="p">
    <p-splitter/>
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
    <p-splitter/>
</xsl:template>

<xsl:template match="text()" priority="2">
    <xsl:choose>

        <xsl:when test="$convert_linebreaks">
            <!--
                We have to use some fake character (U+E000 was chosen here)
                to prevent collapsing lines in cases like <em>p1</em>\n\n<em>p2</em>
            -->
            <xsl:variable name="text" select="re:replace(., '\n\s*\n', 'g', '&#xe000;\n\n&#xe000;')"/>
            <xsl:for-each select="str:split($text, '&#10;&#10;')">
                <xsl:variable name="text_fix_br" select="re:replace(., '\n', 'g', '&#xe000;\n&#xe000;')"/>
                <xsl:for-each select="str:split($text_fix_br, '&#10;')">
                    <text><xsl:value-of select="re:replace(., '&#xe000;', 'g', '')"/></text>
                    <xsl:if test="following-sibling::*">
                        <xsl:choose>
                            <xsl:when test="$br_to_p">
                                <p-splitter/>
                            </xsl:when>
                            <xsl:otherwise>
                                <br/>
                            </xsl:otherwise>
                        </xsl:choose>
                    </xsl:if>
                </xsl:for-each>
                <xsl:if test="following-sibling::*">
                    <p-splitter/>
                </xsl:if>
            </xsl:for-each>
        </xsl:when>

        <xsl:otherwise>
            <text><xsl:value-of select="."/></text>
        </xsl:otherwise>

    </xsl:choose>
</xsl:template>

<xsl:template match="br" priority="2">
    <xsl:choose>

        <xsl:when test="$br_to_p">
            <p-splitter/>
        </xsl:when>

        <xsl:otherwise>
            <xsl:copy>
                <xsl:apply-templates select="@*|node()"/>
            </xsl:copy>
        </xsl:otherwise>

    </xsl:choose>
</xsl:template>

<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>
    
</xsl:stylesheet>
