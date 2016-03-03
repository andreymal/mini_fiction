<?xml version="1.0"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    
<xsl:template match="
            p[not(@root-paragraph)] | text |
            p[not(.//text()[normalize-space(.) != ''] or .//img)] |
            p[.//*/@block-element]
        ">
    <xsl:apply-templates/>
</xsl:template>

<xsl:template match="p-splitter"/>
<xsl:template match="@block-element"/>
<xsl:template match="@root-paragraph"/>

<xsl:template match="@*|node()">
    <xsl:copy>
        <xsl:apply-templates select="@*|node()"/>
    </xsl:copy>
</xsl:template>
    
</xsl:stylesheet>